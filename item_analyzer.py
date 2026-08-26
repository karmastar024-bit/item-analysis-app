import re
import pandas as pd
import numpy as np

from dataclasses import dataclass
from enum import Enum


# ============================================================
# CONFIGURATION
# ============================================================

class ItemRecommendation(Enum):
    RETAIN = "RETAIN"
    REVIEW = "REVIEW"
    REVISE = "REVISE"
    DISCARD = "DISCARD"


# A distractor selected by fewer than 5% of examinees
# is considered non-functional.
NON_FUNCTIONAL_THRESHOLD = 0.05

OPTION_LETTERS = ["A", "B", "C", "D"]


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
        self.student_data = None
        self.scores = None

        self.total_students = 0
        self.total_questions = 0

    # ========================================================
    # LOAD ANSWER KEY
    # ========================================================

    def load_answer_key(self, excel_file):
        """
        Load answer key from Excel.

        Expected format:

        Q1 | Q2 | Q3 | Q4
        A  | B  | C  | D

        Question headers are matched case-insensitively.
        """

        xl_file = pd.ExcelFile(excel_file)

        if not xl_file.sheet_names:
            raise ValueError(
                "The answer key workbook does not contain any sheets."
            )

        sheet_name = xl_file.sheet_names[0]

        df = pd.read_excel(
            excel_file,
            sheet_name=sheet_name,
            header=0
        )

        if df.empty:
            raise ValueError(
                "Answer key sheet has no data rows."
            )

        row = df.iloc[0]

        self.answer_key = {}

        for col in df.columns:

            col_label = str(col).strip()

            # Current supported format:
            # Q1, Q2, Q3...
            if not re.match(
                r"^Q\d+$",
                col_label,
                re.IGNORECASE
            ):
                continue

            answer = str(
                row[col]
            ).upper().strip()

            if answer in OPTION_LETTERS:

                canonical_question = (
                    "Q" +
                    re.search(
                        r"\d+",
                        col_label
                    ).group()
                )

                self.answer_key[
                    canonical_question
                ] = answer

        self.total_questions = len(
            self.answer_key
        )

        if self.total_questions == 0:

            raise ValueError(
                "No valid questions were found in the "
                "answer key. Expected columns such as "
                "Q1, Q2, Q3... with answer letters A-D."
            )

    # ========================================================
    # LOAD STUDENT RESPONSES
    # ========================================================

    def load_student_responses(self, excel_file):

        if self.total_questions == 0:

            raise ValueError(
                "Load the answer key before loading "
                "student responses."
            )

        xl_file = pd.ExcelFile(excel_file)

        if not xl_file.sheet_names:

            raise ValueError(
                "The student-response workbook does not "
                "contain any sheets."
            )

        sheet_name = xl_file.sheet_names[0]

        df = pd.read_excel(
            excel_file,
            sheet_name=sheet_name,
            header=0
        )

        if df.empty:

            raise ValueError(
                "Student response sheet has no data."
            )

        # ----------------------------------------------------
        # Normalize headers
        # ----------------------------------------------------

        normalized = {}

        for col in df.columns:

            normalized[
                str(col).strip().lower()
            ] = col

        # ----------------------------------------------------
        # Find Student ID
        # ----------------------------------------------------

        id_col = next(
            (
                normalized[k]
                for k in (
                    "student id",
                    "studentid",
                    "id",
                    "roll number",
                    "roll no",
                    "roll"
                )
                if k in normalized
            ),
            None
        )

        # ----------------------------------------------------
        # Find Name
        # ----------------------------------------------------

        name_col = next(
            (
                normalized[k]
                for k in (
                    "name",
                    "student name"
                )
                if k in normalized
            ),
            None
        )

        # ----------------------------------------------------
        # Find overall score
        # ----------------------------------------------------

        score_col = next(
            (
                normalized[k]
                for k in (
                    "score",
                    "total score",
                    "total"
                )
                if k in normalized
            ),
            None
        )

        if id_col is None:

            raise ValueError(
                "Could not find a Student ID column. "
                "Expected 'Student ID', 'StudentID', "
                "'ID', 'Roll Number', or 'Roll'."
            )

        if name_col is None:

            raise ValueError(
                "Could not find a Name column. "
                "Expected 'Name' or 'Student Name'."
            )

        # ----------------------------------------------------
        # Match question columns
        # ----------------------------------------------------

        actual_question_columns = {}

        for col in df.columns:

            col_label = str(col).strip()

            match = re.match(
                r"^Q(\d+)$",
                col_label,
                re.IGNORECASE
            )

            if match:

                question_number = match.group(1)

                canonical = (
                    "Q" +
                    question_number
                )

                actual_question_columns[
                    canonical
                ] = col

        missing_questions = [
            q
            for q in self.answer_key.keys()
            if q not in actual_question_columns
        ]

        if missing_questions:

            raise ValueError(
                "The student response file is missing "
                "these question columns: "
                +
                ", ".join(missing_questions)
            )

        # ----------------------------------------------------
        # Read students
        # ----------------------------------------------------

        student_list = []

        for _, row in df.iterrows():

            # Skip completely empty rows
            if row.isna().all():
                continue

            student_id = str(
                row[id_col]
            ).strip()

            student_name = str(
                row[name_col]
            ).strip()

            # -----------------------------------------------
            # Provided overall score
            # -----------------------------------------------

            provided_score = None

            if (
                score_col is not None
                and pd.notna(row[score_col])
            ):

                try:

                    provided_score = float(
                        row[score_col]
                    )

                except (
                    ValueError,
                    TypeError
                ):

                    provided_score = None

            # -----------------------------------------------
            # Responses
            # -----------------------------------------------

            responses = []

            for question in self.answer_key.keys():

                col = actual_question_columns[
                    question
                ]

                response = row[col]

                if pd.notna(response):

                    response = str(
                        response
                    ).upper().strip()

                    if response in OPTION_LETTERS:

                        responses.append(
                            response
                        )

                    else:

                        responses.append(
                            None
                        )

                else:

                    responses.append(None)

            student_list.append({
                "student_id": student_id,
                "name": student_name,
                "responses": responses,
                "provided_score": provided_score
            })

        self.student_data = pd.DataFrame(
            student_list
        )

        self.total_students = len(
            self.student_data
        )

        if self.total_students == 0:

            raise ValueError(
                "No student records were found "
                "in the response file."
            )

    # ========================================================
    # CALCULATE STUDENT SCORES
    # ========================================================

    def calculate_scores(self):

        scores = []

        question_labels = list(
            self.answer_key.keys()
        )

        for responses in (
            self.student_data["responses"]
        ):

            correct = 0

            for i, question in enumerate(
                question_labels
            ):

                if (
                    i < len(responses)
                    and
                    responses[i]
                    ==
                    self.answer_key[question]
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

        self.student_data[
            "percentage"
        ] = (
            self.scores
            /
            self.total_questions
        ) * 100

    # ========================================================
    # ITEM STATISTICS
    # ========================================================

    def calculate_item_statistics(self):

        if self.total_students == 0:

            return []

        # ----------------------------------------------------
        # Upper/lower group size
        # ----------------------------------------------------

        group_size = max(
            1,
            int(
                self.total_students * 0.27
            )
        )

        # ----------------------------------------------------
        # Determine ranking score
        # ----------------------------------------------------

        if (
            "provided_score"
            in self.student_data.columns
            and
            self.student_data[
                "provided_score"
            ].notna().all()
        ):

            grouping_scores = (
                self.student_data[
                    "provided_score"
                ].to_numpy()
            )

        else:

            grouping_scores = self.scores

        sorted_indices = np.argsort(
            -grouping_scores
        )

        upper_group = (
            sorted_indices[:group_size]
        )

        lower_group = (
            sorted_indices[-group_size:]
        )

        # ----------------------------------------------------
        # Calculate each item
        # ----------------------------------------------------

        item_stats = []

        question_labels = list(
            self.answer_key.keys()
        )

        for q_idx, q_label in enumerate(
            question_labels
        ):

            correct_answer = (
                self.answer_key[q_label]
            )

            # -----------------------------------------------
            # Correct responses
            # -----------------------------------------------

            correct_count = 0

            for responses in (
                self.student_data[
                    "responses"
                ]
            ):

                if (
                    q_idx < len(responses)
                    and
                    responses[q_idx]
                    ==
                    correct_answer
                ):

                    correct_count += 1

            # -----------------------------------------------
            # Upper group
            # -----------------------------------------------

            upper_correct = 0

            for index in upper_group:

                responses = (
                    self.student_data.iloc[
                        index
                    ]["responses"]
                )

                if (
                    q_idx < len(responses)
                    and
                    responses[q_idx]
                    ==
                    correct_answer
                ):

                    upper_correct += 1

            # -----------------------------------------------
            # Lower group
            # -----------------------------------------------

            lower_correct = 0

            for index in lower_group:

                responses = (
                    self.student_data.iloc[
                        index
                    ]["responses"]
                )

                if (
                    q_idx < len(responses)
                    and
                    responses[q_idx]
                    ==
                    correct_answer
                ):

                    lower_correct += 1

            # -----------------------------------------------
            # Difficulty
            # -----------------------------------------------

            difficulty = (
                correct_count
                /
                self.total_students
            )

            # -----------------------------------------------
            # Discrimination
            # -----------------------------------------------

            discrimination = (
                upper_correct / group_size
            ) - (
                lower_correct / group_size
            )

            # -----------------------------------------------
            # Difficulty interpretation
            # -----------------------------------------------

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

            # -----------------------------------------------
            # Discrimination interpretation
            # -----------------------------------------------

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

            # =================================================
            # DISTRACTOR ANALYSIS
            # =================================================

            option_counts = {
                option: 0
                for option in OPTION_LETTERS
            }

            omitted_count = 0

            for responses in (
                self.student_data[
                    "responses"
                ]
            ):

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

            for option in OPTION_LETTERS:

                count = option_counts[
                    option
                ]

                percentage = (
                    count
                    /
                    self.total_students
                ) * 100

                is_correct = (
                    option
                    ==
                    correct_answer
                )

                # Correct answer is not evaluated
                # as a distractor.
                if is_correct:

                    is_functional = True

                else:

                    distractor_total += 1

                    is_functional = (
                        percentage
                        >=
                        NON_FUNCTIONAL_THRESHOLD
                        * 100
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

            # -----------------------------------------------
            # Distractor efficiency
            # -----------------------------------------------

            if distractor_total > 0:

                distractor_efficiency = (
                    functional_distractor_count
                    /
                    distractor_total
                ) * 100

            else:

                distractor_efficiency = 0

            omitted_percentage = (
                omitted_count
                /
                self.total_students
            ) * 100

            # =================================================
            # RECOMMENDATION
            # =================================================

            if discrimination < 0:

                recommendation = (
                    ItemRecommendation.DISCARD
                )

            elif (
                discrimination < 0.20
                and
                (
                    difficulty < 0.20
                    or
                    difficulty > 0.80
                )
            ):

                recommendation = (
                    ItemRecommendation.REVISE
                )

            elif (
                discrimination < 0.20
                or
                difficulty < 0.20
                or
                difficulty > 0.80
            ):

                recommendation = (
                    ItemRecommendation.REVIEW
                )

            else:

                recommendation = (
                    ItemRecommendation.RETAIN
                )

            # -----------------------------------------------
            # Store item
            # -----------------------------------------------

            stat = ItemStats(
                question=q_label,
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

        ranked = (
            self.student_data.copy()
        )

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

        return {
            "total_students": (
                self.total_students
            ),

            "total_questions": (
                self.total_questions
            ),

            "mean_score": (
                float(
                    self.scores.mean()
                )
                if len(self.scores) > 0
                else 0
            ),

            "std_score": (
                float(
                    self.scores.std()
                )
                if len(self.scores) > 0
                else 0
            ),

            "min_score": (
                int(
                    self.scores.min()
                )
                if len(self.scores) > 0
                else 0
            ),

            "max_score": (
                int(
                    self.scores.max()
                )
                if len(self.scores) > 0
                else 0
            ),

            "mean_percentage": (
                float(
                    self.scores.mean()
                    /
                    self.total_questions
                    *
                    100
                )
                if (
                    len(self.scores) > 0
                    and
                    self.total_questions > 0
                )
                else 0
            )
        }

    # ========================================================
    # RUN COMPLETE ANALYSIS
    # ========================================================

    def run_analysis(
        self,
        answer_key_file,
        student_data_file
    ):

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

        return {
            "summary": summary,
            "items": items,
            "students": students
        }
