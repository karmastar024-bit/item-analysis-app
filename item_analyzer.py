import re
import pandas as pd
import numpy as np

from dataclasses import dataclass
from enum import Enum


# ============================================================
# CONSTANTS
# ============================================================

NON_FUNCTIONAL_THRESHOLD = 0.05

OPTION_LETTERS = ["A", "B", "C", "D"]


# ============================================================
# ENUMS
# ============================================================

class ItemRecommendation(Enum):
    RETAIN = "RETAIN"
    REVIEW = "REVIEW"
    REVISE = "REVISE"
    DISCARD = "DISCARD"


# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class DistractorOption:
    option: str
    count: int
    percentage: float
    is_correct: bool
    is_functional: bool


@dataclass
class ItemStats:
    question: str
    question_number: int
    correct_answer: str

    correct_count: int
    total_students: int

    difficulty: float
    discrimination: float

    recommendation: ItemRecommendation

    difficulty_status: str
    discrimination_status: str

    distractor_efficiency: float
    non_functional_distractors: list

    option_breakdown: list

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


# ============================================================
# ITEM ANALYZER
# ============================================================

class ItemAnalyzer:

    def __init__(self):

        self.answer_key = {}

        # Example:
        # {
        #     "Q1": "A",
        #     "Q2": "B",
        #     "Q3": "C"
        # }

        self.question_columns = []

        self.student_data = None
        self.scores = None

        self.total_students = 0
        self.total_questions = 0

    # ========================================================
    # NORMALIZE QUESTION LABEL
    # ========================================================

    def normalize_question_label(self, label):

        """
        Convert many possible question labels into a standard format.

        Examples:

            Q1          -> Q1
            q1          -> Q1
            Q 1         -> Q1
            Question 1  -> Q1
            question_1  -> Q1
            Item 1      -> Q1
            item 1      -> Q1
            1           -> Q1
            1.          -> Q1
            Q-1         -> Q1
        """

        if pd.isna(label):
            return None

        text = str(label).strip()

        if not text:
            return None

        # Normalize spaces
        text = re.sub(r"\s+", " ", text)

        # Look for a number
        match = re.search(r"(\d+)", text)

        if match:
            number = int(match.group(1))
            return f"Q{number}"

        return None

    # ========================================================
    # FIND QUESTION COLUMNS
    # ========================================================

    def detect_question_columns(self, columns):

        """
        Detect question columns regardless of whether the original
        labels are Q1, q1, Question 1, 1, Item 1, etc.

        Returns:

            {
                "Q1": original_column_name,
                "Q2": original_column_name,
                ...
            }
        """

        detected = {}

        for col in columns:

            normalized = self.normalize_question_label(col)

            if normalized is None:
                continue

            # Avoid accidental duplicate question numbers
            if normalized not in detected:
                detected[normalized] = col

        # Sort numerically
        detected = dict(
            sorted(
                detected.items(),
                key=lambda x: int(
                    re.search(r"\d+", x[0]).group()
                )
            )
        )

        return detected

    # ========================================================
    # VALIDATE ANSWER
    # ========================================================

    def normalize_answer(self, value):

        if pd.isna(value):
            return None

        text = str(value).strip().upper()

        # Remove spaces and punctuation
        text = re.sub(r"[^A-Z]", "", text)

        if text in OPTION_LETTERS:
            return text

        return None

    # ========================================================
    # LOAD ANSWER KEY
    # ========================================================

    def load_answer_key(self, excel_file):

        """
        Load answer key.

        Supports formats such as:

        Q1 Q2 Q3 Q4
        A  B  C  D

        q1 q2 q3 q4
        a  b  c  d

        1  2  3  4
        A  B  C  D

        Question 1 Question 2 Question 3
        A          B          C
        """

        xl_file = pd.ExcelFile(excel_file)

        if not xl_file.sheet_names:
            raise ValueError("The answer key workbook contains no worksheets.")

        sheet_name = xl_file.sheet_names[0]

        df = pd.read_excel(
            excel_file,
            sheet_name=sheet_name,
            header=0
        )

        if df.empty:
            raise ValueError(
                "The answer key sheet is empty."
            )

        print(
            f"Loading answer key from sheet: {sheet_name}"
        )

        print(
            f"Answer key shape: {df.shape}"
        )

        # ----------------------------------------------------
        # Detect question columns
        # ----------------------------------------------------

        detected = self.detect_question_columns(
            df.columns
        )

        # ----------------------------------------------------
        # If no question columns were detected,
        # try to interpret columns positionally.
        # ----------------------------------------------------

        if not detected:

            possible_columns = []

            for col in df.columns:

                # Ignore obvious metadata columns
                name = str(col).strip().lower()

                if name in [
                    "answer",
                    "correct answer",
                    "correct",
                    "key",
                    "answer key",
                    "student id",
                    "name",
                    "score",
                    "total",
                ]:
                    continue

                possible_columns.append(col)

            for index, col in enumerate(possible_columns, start=1):

                if index <= len(df.columns):

                    sample_values = df[col].dropna()

                    if len(sample_values) == 0:
                        continue

                    normalized_answers = [
                        self.normalize_answer(v)
                        for v in sample_values
                    ]

                    if any(
                        answer in OPTION_LETTERS
                        for answer in normalized_answers
                    ):
                        detected[f"Q{index}"] = col

        if not detected:

            raise ValueError(
                "No valid questions were found in the answer key. "
                "Please use question columns such as Q1, Q2, Q3... "
                "or Question 1, Question 2... or simply 1, 2, 3..."
            )

        # ----------------------------------------------------
        # Determine which row contains the answer key
        # ----------------------------------------------------

        answer_row = None

        # Usually the first data row
        for row_index in range(len(df)):

            row = df.iloc[row_index]

            valid_answers = 0

            for original_col in detected.values():

                answer = self.normalize_answer(
                    row[original_col]
                )

                if answer in OPTION_LETTERS:
                    valid_answers += 1

            if valid_answers > 0:

                answer_row = row
                break

        if answer_row is None:

            raise ValueError(
                "Question columns were detected, but no valid answer "
                "letters A-D were found in the answer key."
            )

        # ----------------------------------------------------
        # Build normalized answer key
        # ----------------------------------------------------

        self.answer_key = {}

        for q_label, original_col in detected.items():

            answer = self.normalize_answer(
                answer_row[original_col]
            )

            if answer in OPTION_LETTERS:

                self.answer_key[q_label] = answer

                print(
                    f"  {q_label}: {answer}"
                )

        self.question_columns = list(
            self.answer_key.keys()
        )

        self.total_questions = len(
            self.answer_key
        )

        print(
            f"Loaded {self.total_questions} questions."
        )

        if self.total_questions == 0:

            raise ValueError(
                "No valid answers A-D were found in the answer key."
            )

    # ========================================================
    # LOAD STUDENT RESPONSES
    # ========================================================

    def load_student_responses(self, excel_file):

        if self.total_questions == 0:

            raise ValueError(
                "Load the answer key before loading student responses."
            )

        xl_file = pd.ExcelFile(excel_file)

        if not xl_file.sheet_names:

            raise ValueError(
                "The student response workbook contains no worksheets."
            )

        sheet_name = xl_file.sheet_names[0]

        df = pd.read_excel(
            excel_file,
            sheet_name=sheet_name,
            header=0
        )

        if df.empty:

            raise ValueError(
                "The student response sheet is empty."
            )

        print(
            f"Loading student responses from sheet: {sheet_name}"
        )

        # ----------------------------------------------------
        # Normalize column names
        # ----------------------------------------------------

        normalized = {
            str(c).strip().lower(): c
            for c in df.columns
        }

        # ----------------------------------------------------
        # Detect ID
        # ----------------------------------------------------

        id_col = None

        for candidate in [
            "student id",
            "studentid",
            "id",
            "roll number",
            "roll no",
            "roll",
            "student number",
        ]:

            if candidate in normalized:

                id_col = normalized[candidate]
                break

        # ----------------------------------------------------
        # Detect name
        # ----------------------------------------------------

        name_col = None

        for candidate in [
            "name",
            "student name",
            "student",
        ]:

            if candidate in normalized:

                name_col = normalized[candidate]
                break

        # ----------------------------------------------------
        # Detect score
        # ----------------------------------------------------

        score_col = None

        for candidate in [
            "score",
            "total score",
            "total",
            "overall score",
            "overall",
            "marks",
            "total marks",
        ]:

            if candidate in normalized:

                score_col = normalized[candidate]
                break

        # ----------------------------------------------------
        # ID is optional
        # ----------------------------------------------------

        if name_col is None:

            raise ValueError(
                "Could not find a Name column in the student response sheet."
            )

        # ----------------------------------------------------
        # Detect question columns
        # ----------------------------------------------------

        detected_student_questions = (
            self.detect_question_columns(df.columns)
        )

        # ----------------------------------------------------
        # Student records
        # ----------------------------------------------------

        student_list = []

        for row_index, row in df.iterrows():

            student_id = ""

            if id_col is not None:

                value = row[id_col]

                if pd.notna(value):

                    student_id = str(value).strip()

            student_name = str(
                row[name_col]
            ).strip()

            # Ignore completely blank student rows
            if (
                not student_name
                or student_name.lower() == "nan"
            ):
                continue

            provided_score = None

            if score_col is not None:

                value = row[score_col]

                if pd.notna(value):

                    try:

                        provided_score = float(value)

                    except (
                        ValueError,
                        TypeError
                    ):

                        provided_score = None

            responses = []

            for q_label in self.question_columns:

                original_col = detected_student_questions.get(
                    q_label
                )

                if original_col is None:

                    responses.append(None)
                    continue

                response = self.normalize_answer(
                    row[original_col]
                )

                responses.append(response)

            student_list.append({

                "student_id": student_id,

                "name": student_name,

                "responses": responses,

                "provided_score": provided_score

            })

        if not student_list:

            raise ValueError(
                "No student records were found in the response sheet."
            )

        self.student_data = pd.DataFrame(
            student_list
        )

        self.total_students = len(
            self.student_data
        )

        print(
            f"Loaded {self.total_students} students."
        )

    # ========================================================
    # CALCULATE STUDENT SCORES
    # ========================================================

    def calculate_scores(self):

        scores = []

        for responses in self.student_data[
            "responses"
        ]:

            correct = 0

            for index, q_label in enumerate(
                self.question_columns
            ):

                if (
                    index < len(responses)
                    and responses[index]
                    == self.answer_key[q_label]
                ):

                    correct += 1

            scores.append(correct)

        self.scores = np.array(
            scores,
            dtype=int
        )

        self.student_data[
            "score"
        ] = self.scores

        if self.total_questions > 0:

            self.student_data[
                "percentage"
            ] = (
                self.scores
                / self.total_questions
                * 100
            )

        else:

            self.student_data[
                "percentage"
            ] = 0

        if len(self.scores) > 0:

            print(
                f"Mean score: {self.scores.mean():.2f}"
            )

    # ========================================================
    # CALCULATE ITEM STATISTICS
    # ========================================================

    def calculate_item_statistics(self):

        if self.total_students == 0:

            return []

        group_size = max(
            1,
            int(
                self.total_students * 0.27
            )
        )

        # ----------------------------------------------------
        # Use provided overall score for discrimination ranking
        # ----------------------------------------------------

        if (
            "provided_score"
            in self.student_data.columns
            and self.student_data[
                "provided_score"
            ].notna().any()
        ):

            grouping_scores = (
                self.student_data[
                    "provided_score"
                ]
                .fillna(
                    self.student_data["score"]
                )
                .to_numpy()
            )

            print(
                "Using provided Score column for upper/lower grouping."
            )

        else:

            grouping_scores = self.scores

            print(
                "Using calculated MCQ score for upper/lower grouping."
            )

        sorted_indices = np.argsort(
            -grouping_scores
        )

        upper_group = sorted_indices[
            :group_size
        ]

        lower_group = sorted_indices[
            -group_size:
        ]

        item_stats = []

        # ----------------------------------------------------
        # Analyze each question
        # ----------------------------------------------------

        for q_idx, q_label in enumerate(
            self.question_columns
        ):

            correct_answer = self.answer_key[
                q_label
            ]

            # ------------------------------------------------
            # Correct count
            # ------------------------------------------------

            correct_count = 0

            for responses in self.student_data[
                "responses"
            ]:

                if (
                    q_idx < len(responses)
                    and responses[q_idx]
                    == correct_answer
                ):

                    correct_count += 1

            # ------------------------------------------------
            # Upper group
            # ------------------------------------------------

            upper_correct = 0

            for student_index in upper_group:

                responses = (
                    self.student_data.iloc[
                        student_index
                    ]["responses"]
                )

                if (
                    q_idx < len(responses)
                    and responses[q_idx]
                    == correct_answer
                ):

                    upper_correct += 1

            # ------------------------------------------------
            # Lower group
            # ------------------------------------------------

            lower_correct = 0

            for student_index in lower_group:

                responses = (
                    self.student_data.iloc[
                        student_index
                    ]["responses"]
                )

                if (
                    q_idx < len(responses)
                    and responses[q_idx]
                    == correct_answer
                ):

                    lower_correct += 1

            # ------------------------------------------------
            # Difficulty
            # ------------------------------------------------

            difficulty = (
                correct_count
                / self.total_students
            )

            # ------------------------------------------------
            # Discrimination
            # ------------------------------------------------

            discrimination = (
                upper_correct / group_size
            ) - (
                lower_correct / group_size
            )

            # ------------------------------------------------
            # Difficulty interpretation
            # ------------------------------------------------

            if difficulty < 0.20:

                difficulty_status = (
                    "Very Difficult"
                )

            elif difficulty > 0.80:

                difficulty_status = (
                    "Too Easy"
                )

            else:

                difficulty_status = (
                    "Ideal"
                )

            # ------------------------------------------------
            # Discrimination interpretation
            # ------------------------------------------------

            if discrimination < 0:

                discrimination_status = (
                    "Negative"
                )

            elif discrimination < 0.20:

                discrimination_status = (
                    "Poor"
                )

            else:

                discrimination_status = (
                    "Good"
                )

            # ------------------------------------------------
            # Option analysis
            # ------------------------------------------------

            option_counts = {
                option: 0
                for option in OPTION_LETTERS
            }

            omitted_count = 0

            for responses in self.student_data[
                "responses"
            ]:

                response = (
                    responses[q_idx]
                    if q_idx < len(responses)
                    else None
                )

                if response in option_counts:

                    option_counts[
                        response
                    ] += 1

                else:

                    omitted_count += 1

            option_breakdown = []

            non_functional_distractors = []

            distractor_total = 0
            functional_distractor_count = 0

            # ------------------------------------------------
            # Analyze A-D
            # ------------------------------------------------

            for option in OPTION_LETTERS:

                count = option_counts[
                    option
                ]

                percentage = (
                    count
                    / self.total_students
                    * 100
                )

                is_correct = (
                    option
                    == correct_answer
                )

                if is_correct:

                    is_functional = True

                else:

                    distractor_total += 1

                    is_functional = (
                        percentage
                        >= (
                            NON_FUNCTIONAL_THRESHOLD
                            * 100
                        )
                    )

                    if is_functional:

                        functional_distractor_count += 1

                    else:

                        non_functional_distractors.append(
                            option
                        )

                option_breakdown.append(
                    DistractorOption(
                        option=option,
                        count=count,
                        percentage=percentage,
                        is_correct=is_correct,
                        is_functional=is_functional
                    )
                )

            # ------------------------------------------------
            # Distractor efficiency
            # ------------------------------------------------

            if distractor_total > 0:

                distractor_efficiency = (
                    functional_distractor_count
                    / distractor_total
                    * 100
                )

            else:

                distractor_efficiency = 0

            omitted_percentage = (
                omitted_count
                / self.total_students
                * 100
            )

            # ------------------------------------------------
            # Recommendation
            # ------------------------------------------------

            if discrimination < 0:

                recommendation = (
                    ItemRecommendation.DISCARD
                )

            elif (
                discrimination < 0.20
                and (
                    difficulty < 0.20
                    or difficulty > 0.80
                )
            ):

                recommendation = (
                    ItemRecommendation.REVISE
                )

            elif (
                discrimination < 0.20
                or difficulty < 0.20
                or difficulty > 0.80
            ):

                recommendation = (
                    ItemRecommendation.REVIEW
                )

            else:

                recommendation = (
                    ItemRecommendation.RETAIN
                )

            # ------------------------------------------------
            # Store item
            # ------------------------------------------------

            question_number = int(
                re.search(
                    r"\d+",
                    q_label
                ).group()
            )

            stat = ItemStats(

                question=q_label,

                question_number=question_number,

                correct_answer=correct_answer,

                correct_count=correct_count,

                total_students=self.total_students,

                difficulty=difficulty,

                discrimination=discrimination,

                recommendation=recommendation,

                difficulty_status=difficulty_status,

                discrimination_status=discrimination_status,

                distractor_efficiency=distractor_efficiency,

                non_functional_distractors=(
                    non_functional_distractors
                ),

                option_breakdown=option_breakdown,

                omitted_count=omitted_count,

                omitted_percentage=omitted_percentage
            )

            item_stats.append(stat)

        return item_stats

    # ========================================================
    # RANK STUDENTS
    # ========================================================

    def rank_students(self):

        ranked = self.student_data.copy()

        ranked["rank"] = (
            ranked["score"]
            .rank(
                method="min",
                ascending=False
            )
            .astype(int)
        )

        ranked = ranked.sort_values(
            ["rank", "name"]
        )

        stats = []

        for _, row in ranked.iterrows():

            stats.append(
                StudentStats(

                    rank=int(
                        row["rank"]
                    ),

                    student_id=str(
                        row["student_id"]
                    ),

                    name=str(
                        row["name"]
                    ),

                    score=int(
                        row["score"]
                    ),

                    percentage=float(
                        row["percentage"]
                    ),

                    responses=row[
                        "responses"
                    ],

                    correct_count=int(
                        row["score"]
                    )
                )
            )

        return stats

    # ========================================================
    # SUMMARY
    # ========================================================

    def get_summary(self):

        if (
            self.scores is None
            or len(self.scores) == 0
        ):

            return {
                "total_students": 0,
                "total_questions": self.total_questions,
                "mean_score": 0,
                "std_score": 0,
                "min_score": 0,
                "max_score": 0,
                "mean_percentage": 0
            }

        return {

            "total_students":
                self.total_students,

            "total_questions":
                self.total_questions,

            "mean_score":
                float(
                    self.scores.mean()
                ),

            "std_score":
                float(
                    self.scores.std(
                        ddof=0
                    )
                ),

            "min_score":
                int(
                    self.scores.min()
                ),

            "max_score":
                int(
                    self.scores.max()
                ),

            "mean_percentage":
                float(
                    (
                        self.scores.mean()
                        / self.total_questions
                        * 100
                    )
                )
                if self.total_questions > 0
                else 0
        }

    # ========================================================
    # COMPLETE ANALYSIS
    # ========================================================

    def run_analysis(
        self,
        answer_key_file,
        student_data_file
    ):

        print(
            "\n=== Starting Analysis ==="
        )

        self.load_answer_key(
            answer_key_file
        )

        self.load_student_responses(
            student_data_file
        )

        self.calculate_scores()

        items = (
            self.calculate_item_statistics()
        )

        students = (
            self.rank_students()
        )

        summary = (
            self.get_summary()
        )

        print(
            "=== Analysis Complete ===\n"
        )

        return {

            "summary":
                summary,

            "items":
                items,

            "students":
                students
        }
