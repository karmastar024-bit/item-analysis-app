import re
import pandas as pd
import numpy as np
from dataclasses import dataclass, asdict
from enum import Enum

class ItemRecommendation(Enum):
    RETAIN = "RETAIN"
    REVIEW = "REVIEW"
    REVISE = "REVISE"
    DISCARD = "DISCARD"

# A distractor chosen by fewer than this fraction of examinees is
# considered "non-functional" (standard item-analysis threshold, ~5%).
NON_FUNCTIONAL_THRESHOLD = 0.05

OPTION_LETTERS = ['A', 'B', 'C', 'D']

@dataclass
class DistractorOption:
    option: str
    count: int
    percentage: float
    is_correct: bool
    is_functional: bool  # True for the correct answer itself; N/A-as-True

@dataclass
class ItemStats:
    question: str
    correct_count: int
    total_students: int
    difficulty: float
    discrimination: float
    recommendation: ItemRecommendation
    difficulty_status: str
    discrimination_status: str
    distractor_efficiency: float          # % of distractors that are functional
    non_functional_distractors: list      # option letters, e.g. ['C', 'D']
    option_breakdown: list                # list[DistractorOption], all options A-D
    omitted_count: int
    omitted_percentage: float

@dataclass
class StudentStats:
    rank: int
    student_id: str
    name: str
    score: int
    percentage: float
    responses: list
    correct_count: int

class ItemAnalyzer:
    def __init__(self):
        self.answer_key = {}
        self.student_data = None
        self.scores = None
        self.total_students = 0
        self.total_questions = 0

    def load_answer_key(self, excel_file):
        """Load answer key - auto-detects sheet name.

        Supports the wide, single-row format actually produced by the
        upload form:

            #Answer key      Q1  Q2  Q3 ...
            Correct Answer    A   B   C ...

        Each column whose header looks like a question label (Q1, Q2, ...)
        is read for its answer letter from the first data row.
        """
        xl_file = pd.ExcelFile(excel_file)
        sheet_name = xl_file.sheet_names[0]
        print(f"Loading answer key from sheet: {sheet_name}")
        df = pd.read_excel(excel_file, sheet_name=sheet_name, header=0)

        print(f"DataFrame shape: {df.shape}")
        print(f"First few rows:\n{df.head()}")

        if df.empty:
            raise ValueError("Answer key sheet has no data rows")

        row = df.iloc[0]
        self.answer_key = {}

        for col in df.columns:
            col_label = str(col).strip()
            if not re.match(r'^Q\d+$', col_label, re.IGNORECASE):
                continue
            answer = str(row[col]).upper().strip()
            if answer in ['A', 'B', 'C', 'D']:
                self.answer_key[col_label] = answer
                print(f"  {col_label}: {answer}")

        self.total_questions = len(self.answer_key)
        print(f"✓ Loaded {self.total_questions} questions")

        if self.total_questions == 0:
            raise ValueError(
                "No valid questions found in answer key. Expected columns "
                "named Q1, Q2, ... with answer letters A-D in the first row."
            )

    def load_student_responses(self, excel_file):
        """Load student responses - auto-detects sheet name.

        Supports the wide format actually produced by the upload form:

            Student ID  Name  Score  Q1  Q2  Q3 ...

        Responses are matched to the answer key by column name (Q1, Q2, ...)
        rather than by position, so extra/unused question columns (e.g. a
        template with Q1-Q30 when only Q1-Q10 are used) are ignored safely.
        """
        if self.total_questions == 0:
            raise ValueError("Load the answer key before loading student responses")

        xl_file = pd.ExcelFile(excel_file)
        sheet_name = xl_file.sheet_names[0]
        print(f"Loading student data from sheet: {sheet_name}")
        df = pd.read_excel(excel_file, sheet_name=sheet_name, header=0)

        print(f"DataFrame shape: {df.shape}")
        print(f"First few rows:\n{df.head()}")

        # Find the ID, Name, and (provided) Score columns by header, case/spacing-insensitive
        normalized = {str(c).strip().lower(): c for c in df.columns}
        id_col = next((normalized[k] for k in ('student id', 'studentid', 'id') if k in normalized), None)
        name_col = next((normalized[k] for k in ('name', 'student name') if k in normalized), None)
        score_col = next((normalized[k] for k in ('score', 'total score', 'total') if k in normalized), None)

        if id_col is None or name_col is None:
            raise ValueError(
                "Could not find 'Student ID' and 'Name' columns in student data sheet"
            )

        if score_col is None:
            print("⚠ Warning: no 'Score' column found in student data; discrimination "
                  "grouping will fall back to the recomputed MCQ score.")

        question_cols = list(self.answer_key.keys())
        missing_cols = [q for q in question_cols if q not in df.columns]
        if missing_cols:
            print(f"⚠ Warning: student data is missing columns for: {missing_cols}")

        student_list = []

        for _, row in df.iterrows():
            student_id = str(row[id_col]).strip()
            student_name = str(row[name_col]).strip()

            provided_score = None
            if score_col is not None and pd.notna(row[score_col]):
                try:
                    provided_score = float(row[score_col])
                except (ValueError, TypeError):
                    provided_score = None

            responses = []
            for q in question_cols:
                response = row[q] if q in df.columns else None
                if pd.notna(response):
                    response = str(response).upper().strip()
                    responses.append(response if response in ['A', 'B', 'C', 'D'] else None)
                else:
                    responses.append(None)

            student_list.append({
                'student_id': student_id,
                'name': student_name,
                'responses': responses,
                'provided_score': provided_score
            })

        self.student_data = pd.DataFrame(student_list)
        self.total_students = len(self.student_data)
        print(f"✓ Loaded {self.total_students} students")

    def calculate_scores(self):
        """Calculate scores for all students"""
        scores = []
        for responses in self.student_data['responses']:
            correct = 0
            for i, q_label in enumerate(self.answer_key.keys()):
                if i < len(responses) and responses[i] == self.answer_key[q_label]:
                    correct += 1
            scores.append(correct)
        
        self.scores = np.array(scores)
        self.student_data['score'] = self.scores
        self.student_data['percentage'] = (self.scores / self.total_questions) * 100
        print(f"✓ Calculated scores (Mean: {self.scores.mean():.2f})")

    def calculate_item_statistics(self):
        """Calculate difficulty and discrimination for each item.

        The upper/lower 27% groups used for the discrimination index are
        determined by the 'Score' column provided in the student data
        Excel file (not the recomputed MCQ-only score), since that column
        may reflect a broader assessment (e.g. MCQ + other sections).
        """
        group_size = max(1, int(self.total_students * 0.27))

        if 'provided_score' in self.student_data.columns and self.student_data['provided_score'].notna().all():
            grouping_scores = self.student_data['provided_score'].to_numpy()
            print("Using provided 'Score' column from Excel for upper/lower group ranking")
        else:
            print("⚠ Provided 'Score' column missing or incomplete; falling back to recomputed MCQ score for grouping")
            grouping_scores = self.scores

        sorted_indices = np.argsort(-grouping_scores)
        upper_group = sorted_indices[:group_size]
        lower_group = sorted_indices[-group_size:]
        
        item_stats = []
        question_labels = list(self.answer_key.keys())
        
        for q_idx, q_label in enumerate(question_labels):
            correct_answer = self.answer_key[q_label]
            
            correct_count = sum(
                1 for r in self.student_data['responses'] 
                if q_idx < len(r) and r[q_idx] == correct_answer
            )
            
            upper_correct = sum(
                1 for i in upper_group 
                if q_idx < len(self.student_data.iloc[i]['responses']) 
                and self.student_data.iloc[i]['responses'][q_idx] == correct_answer
            )
            
            lower_correct = sum(
                1 for i in lower_group 
                if q_idx < len(self.student_data.iloc[i]['responses']) 
                and self.student_data.iloc[i]['responses'][q_idx] == correct_answer
            )
            
            difficulty = correct_count / self.total_students if self.total_students > 0 else 0
            discrimination = (upper_correct / group_size) - (lower_correct / group_size) if group_size > 0 else 0
            
            if difficulty < 0.20:
                difficulty_status = "Very Difficult"
            elif difficulty > 0.80:
                difficulty_status = "Too Easy"
            else:
                difficulty_status = "Ideal"
            
            if discrimination < 0:
                discrimination_status = "Negative"
            elif discrimination < 0.20:
                discrimination_status = "Poor"
            else:
                discrimination_status = "Good"
            
            # --- Distractor analysis ---
            option_counts = {opt: 0 for opt in OPTION_LETTERS}
            omitted_count = 0
            for r in self.student_data['responses']:
                response = r[q_idx] if q_idx < len(r) else None
                if response in option_counts:
                    option_counts[response] += 1
                else:
                    omitted_count += 1

            option_breakdown = []
            non_functional_distractors = []
            distractor_total = 0
            functional_distractor_count = 0

            for opt in OPTION_LETTERS:
                count = option_counts[opt]
                pct = (count / self.total_students * 100) if self.total_students > 0 else 0
                is_correct = (opt == correct_answer)

                if is_correct:
                    is_functional = True
                else:
                    distractor_total += 1
                    is_functional = pct >= (NON_FUNCTIONAL_THRESHOLD * 100)
                    if is_functional:
                        functional_distractor_count += 1
                    else:
                        non_functional_distractors.append(opt)

                option_breakdown.append(DistractorOption(
                    option=opt,
                    count=count,
                    percentage=pct,
                    is_correct=is_correct,
                    is_functional=is_functional
                ))

            distractor_efficiency = (
                (functional_distractor_count / distractor_total * 100)
                if distractor_total > 0 else 0
            )
            omitted_percentage = (
                (omitted_count / self.total_students * 100) if self.total_students > 0 else 0
            )

            if discrimination < 0:
                rec = ItemRecommendation.DISCARD
            elif discrimination < 0.20 and (difficulty < 0.20 or difficulty > 0.80):
                rec = ItemRecommendation.REVISE
            elif discrimination < 0.20 or (difficulty < 0.20 or difficulty > 0.80):
                rec = ItemRecommendation.REVIEW
            else:
                rec = ItemRecommendation.RETAIN
            
            stat = ItemStats(
                question=q_label,
                correct_count=correct_count,
                total_students=self.total_students,
                difficulty=difficulty,
                discrimination=discrimination,
                recommendation=rec,
                difficulty_status=difficulty_status,
                discrimination_status=discrimination_status,
                distractor_efficiency=distractor_efficiency,
                non_functional_distractors=non_functional_distractors,
                option_breakdown=option_breakdown,
                omitted_count=omitted_count,
                omitted_percentage=omitted_percentage
            )
            item_stats.append(stat)
        
        return item_stats

    def rank_students(self):
        """Rank students by score"""
        ranked = self.student_data.copy()
        ranked['rank'] = ranked['score'].rank(method='min', ascending=False).astype(int)
        ranked = ranked.sort_values('rank')
        
        stats = []
        for _, row in ranked.iterrows():
            stats.append(StudentStats(
                rank=int(row['rank']),
                student_id=row['student_id'],
                name=row['name'],
                score=int(row['score']),
                percentage=float(row['percentage']),
                responses=row['responses'],
                correct_count=int(row['score'])
            ))
        return stats

    def get_summary(self):
        """Get summary statistics"""
        return {
            'total_students': self.total_students,
            'total_questions': self.total_questions,
            'mean_score': float(self.scores.mean()) if len(self.scores) > 0 else 0,
            'std_score': float(self.scores.std()) if len(self.scores) > 0 else 0,
            'min_score': int(self.scores.min()) if len(self.scores) > 0 else 0,
            'max_score': int(self.scores.max()) if len(self.scores) > 0 else 0,
            'mean_percentage': float((self.scores.mean() / self.total_questions * 100)) if len(self.scores) > 0 and self.total_questions > 0 else 0,
            'pass_rate': float((sum(self.scores >= 50) / self.total_students * 100)) if self.total_students > 0 else 0
        }

    def run_analysis(self, answer_key_file, student_data_file):
        """Run complete analysis"""
        print("\n=== Starting Analysis ===")
        self.load_answer_key(answer_key_file)
        self.load_student_responses(student_data_file)
        self.calculate_scores()
        items = self.calculate_item_statistics()
        students = self.rank_students()
        summary = self.get_summary()
        print("=== Analysis Complete ===\n")
        return {
            'summary': summary,
            'items': items,
            'students': students
        }