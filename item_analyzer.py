import re
from dataclasses import dataclass
from enum import Enum

import numpy as np
import pandas as pd


# ============================================================
# CONSTANTS
# ============================================================

OPTION_LETTERS = ["A", "B", "C", "D"]

# A distractor selected by fewer than 5% of students
# is considered non-functional.
NON_FUNCTIONAL_THRESHOLD = 0.05


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
# QUESTION NORMALIZATION
# ============================================================

def normalize_question_label(value):
    """
    Convert different question naming styles into a canonical
    question number.

    Examples:

        Q1          -> 1
        q1          -> 1
        Q01         -> 1
        q01         -> 1
        Question 1  -> 1
        question1   -> 1
        QUESTION 01 -> 1
        1           -> 1
        "  Q 1 "    -> 1

    Also handles simple Roman-numeral forms such as:

        QI  -> 1
        QII -> 2
        QIII -> 3
        QIV -> 4

    Returns None if the value does not look like a question label.
    """

    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    # Remove spaces, underscores, hyphens and periods
    cleaned = re.sub(r"[\s_\-\.]+", "", text)

    # Normal Arabic-number formats
    patterns = [
        r"^q(\d+)$",
        r"^question(\d+)$",
        r"^ques(\d+)$",
        r"^qno(\d+)$",
        r"^no(\d+)$",
        r"^(\d+)$",
    ]

    for pattern in patterns:
        match = re.match(pattern, cleaned, re.IGNORECASE)

        if match:
            number = int(match.group(1))

            if number > 0:
                return number

    # Roman numeral support
    roman_patterns = [
        (r"^qi$", 1),
        (r"^qii$", 2),
        (r"^qiii$", 3),
        (r"^qiv$", 4),
        (r"^qv$", 5),
        (r"^qvi$", 6),
        (r"^qvii$", 7),
        (r"^qviii$", 8),
        (r"^qix$", 9),
        (r"^qx$", 10),
    ]

    for pattern, number in roman_patterns:
        if re.match(pattern, cleaned, re.IGNORECASE):
            return number

    return None


# ============================================================
# ANSWER NORMALIZATION
# ============================================================

def normalize_answer(value):
    """
    Convert a response/answer into A-D.

    Accepts:
        A
        a
        A.
        Option A
        option a
        " A "
    """

    if value is None:
        return None

    if pd.isna(value):
        return None

    text = str(value).strip().upper()

    if not text:
        return None

    # Direct A-D
    if text in OPTION_LETTERS:
        return text

    # Remove punctuation
    cleaned = re.sub(r"[\s\.\)\:\-]+", "", text)

    if cleaned in OPTION_LETTERS:
        return cleaned

    # Option A / Answer A etc.
    match = re.search(
        r"(?:OPTION|ANSWER|CHOICE)?([ABCD])$",
        cleaned
    )

    if match:
        return match.group(1)

    return None


# ============================================================
# HEADER ROW DETECTION
# ============================================================
#
# The official templates include a title banner and instructions
# above the real header row, so the header can't be assumed to be
# row 0. These helpers scan the top of the sheet to locate it.

def _normalize_header_text(value):

    text = re.sub(
        r"[\s_\-]+",
        " ",
        str(value).strip().lower()
    )

    return text


def _find_vertical_answer_key_header(raw_df, max_scan_rows=15):
    """
    Scan the top of the answer key sheet for the row containing
    both a 'Question' style column and a 'Correct Answer' style
    column (exact match after whitespace normalization).

    Returns (header_row_index, question_col_idx, answer_col_idx)
    or (None, None, None) if not found.
    """

    question_candidates = {
        "question",
        "question number",
        "question no",
        "item",
        "item number",
        "item no",
        "q"
    }

    answer_candidates = {
        "correct answer",
        "correct",
        "answer",
        "key",
        "correct option"
    }

    scan_limit = min(max_scan_rows, len(raw_df))

    for row_idx in range(scan_limit):

        row = raw_df.iloc[row_idx]

        question_col = None
        answer_col = None

        for col_idx, value in row.items():

            if value is None or str(value).strip() == "":
                continue

            text = _normalize_header_text(value)

            if question_col is None and text in question_candidates:
                question_col = col_idx

            if answer_col is None and text in answer_candidates:
                answer_col = col_idx

        if question_col is not None and answer_col is not None:
            return row_idx, question_col, answer_col

    return None, None, None


def _detect_wide_format_answer_key(raw_df, max_scan_rows=5):
    """
    Look for a header row that instead looks like the (no longer
    accepted) wide format: Q1, Q2, Q3, ... spread across columns.
    """

    scan_limit = min(max_scan_rows, len(raw_df))

    for row_idx in range(scan_limit):

        row = raw_df.iloc[row_idx]

        question_like_columns = [
            col_idx
            for col_idx, value in row.items()
            if value is not None
            and normalize_question_label(value) is not None
        ]

        if len(question_like_columns) >= 2:
            return True

    return False


def _find_student_response_header(raw_df, max_scan_rows=30):
    """
    Scan the top of the student response sheet for the header row:
    the row that contains a student-name-style column together
    with at least one question-numbered column.

    Returns the header row index, or None if not found.
    """

    scan_limit = min(max_scan_rows, len(raw_df))

    for row_idx in range(scan_limit):

        row = raw_df.iloc[row_idx]

        has_name_cue = False
        question_col_count = 0

        for value in row.values:

            if value is None or str(value).strip() == "":
                continue

            text = _normalize_header_text(value)

            if "name" in text:
                has_name_cue = True

            if normalize_question_label(value) is not None:
                question_col_count += 1

        if has_name_cue and question_col_count >= 1:
            return row_idx

    return None


# ============================================================
# EXAM INFO BANNER
# ============================================================
#
# The official student response template has an optional
# "EXAM INFORMATION" banner above the real header row, e.g.:
#
#   EXAM INFORMATION
#
#   Examination Name :   Mid-Term Examination
#   Examination Year :   2026
#   Class :
#   Subject :
#
# This is scanned out here (independent of the header-row
# detection) so it can be carried through to the analysis
# results and stamped onto the downloaded report.

EXAM_INFO_FIELD_LOOKUP = {
    "examination name": "Examination Name",
    "exam name": "Examination Name",
    "examination title": "Examination Name",
    "examination year": "Examination Year",
    "exam year": "Examination Year",
    "year": "Examination Year",
    "class": "Class",
    "grade": "Class",
    "section": "Class",
    "class section": "Class",
    "subject": "Subject",
    "course": "Subject",
}

EXAM_INFO_FIELDS = [
    "Examination Name",
    "Examination Year",
    "Class",
    "Subject"
]


def _extract_exam_info(raw_df, header_row_idx):
    """
    Scan the rows above the detected header row for label/value
    pairs matching the exam-information banner fields. Returns a
    dict with all of EXAM_INFO_FIELDS present, defaulting to ""
    for anything not found or left blank by the user.
    """

    exam_info = {
        field: ""
        for field in EXAM_INFO_FIELDS
    }

    if header_row_idx is None:
        scan_limit = len(raw_df)
    else:
        scan_limit = min(header_row_idx, len(raw_df))

    for row_idx in range(scan_limit):

        row = raw_df.iloc[row_idx]

        row_values = [
            value
            for value in row.values
            if value is not None
            and not pd.isna(value)
            and str(value).strip() != ""
        ]

        if not row_values:
            continue

        label_raw = str(row_values[0]).strip()

        label_clean = re.sub(
            r"[:\s]+$",
            "",
            label_raw
        ).strip().lower()

        label_clean = re.sub(
            r"[\s_\-]+",
            " ",
            label_clean
        )

        if label_clean not in EXAM_INFO_FIELD_LOOKUP:
            continue

        field_name = EXAM_INFO_FIELD_LOOKUP[label_clean]

        if len(row_values) >= 2:
            value = str(row_values[1]).strip()
        else:
            value = ""

        # Keep the first non-blank value found for each field.
        if value and not exam_info[field_name]:
            exam_info[field_name] = value

    return exam_info


# ============================================================
# ITEM ANALYZER
# ============================================================

class ItemAnalyzer:

    def __init__(self):

        self.answer_key = {}
        self.answer_key_labels = {}

        self.student_data = None
        self.scores = None

        self.total_students = 0
        self.total_questions = 0

        self.exam_info = {
            field: ""
            for field in EXAM_INFO_FIELDS
        }

    # ========================================================
    # LOAD ANSWER KEY
    # ========================================================

    def load_answer_key(self, excel_file):

        xl_file = pd.ExcelFile(excel_file)

        if not xl_file.sheet_names:
            raise ValueError("The answer key workbook contains no worksheets.")

        sheet_name = xl_file.sheet_names[0]

        # Read with no assumed header, since the official template
        # has a title banner and instructions above the real
        # 'Question' / 'Correct Answer' header row.
        raw_df = pd.read_excel(
            excel_file,
            sheet_name=sheet_name,
            header=None
        )

        if raw_df.empty and len(raw_df.columns) == 0:
            raise ValueError(
                "The answer key sheet is empty."
            )

        self.answer_key = {}
        self.answer_key_labels = {}

        # ----------------------------------------------------
        # ONLY ACCEPTED FORMAT: VERTICAL
        #
        # Question | Correct Answer
        # Q1       | A
        # Q2       | B
        # ----------------------------------------------------

        header_row_idx, question_col, answer_col = (
            _find_vertical_answer_key_header(raw_df)
        )

        # ----------------------------------------------------
        # DETECT A WIDE-FORMAT UPLOAD AND REJECT IT EXPLICITLY
        #
        # If the sheet looks like Q1 Q2 Q3 ... across a header
        # row instead of Question/Correct Answer columns, give a
        # specific message rather than falling through to the
        # generic "no questions found" error.
        # ----------------------------------------------------

        if header_row_idx is None:

            if _detect_wide_format_answer_key(raw_df):

                raise ValueError(
                    "This answer key is in the wide format "
                    "(one column per question), which is no "
                    "longer accepted.\n\n"
                    "Please use the vertical format instead: a "
                    "'Question' column and a 'Correct Answer' "
                    "column, with one row per question.\n\n"
                    "Download the sample Answer Key template to "
                    "see the required layout."
                )

            raise ValueError(
                "Could not find the required columns in the "
                "answer key.\n\n"
                "The sheet must contain a 'Question' column and "
                "a 'Correct Answer' column, with one row per "
                "question.\n\n"
                "Download the sample Answer Key template to see "
                "the required layout."
            )

        data_rows = raw_df.iloc[header_row_idx + 1:]

        for _, row in data_rows.iterrows():

            question_number = normalize_question_label(
                row[question_col]
            )

            answer = normalize_answer(
                row[answer_col]
            )

            if question_number is not None and answer is not None:

                self.answer_key[question_number] = answer

                self.answer_key_labels[
                    question_number
                ] = str(
                    row[question_col]
                ).strip()

        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        self.total_questions = len(self.answer_key)

        if self.total_questions == 0:

            raise ValueError(
                "No valid questions were found in the answer key.\n\n"
                "The system accepts question labels such as:\n"
                "Q1, q1, Q01, q01, Question 1, question1, 1, etc.\n\n"
                "Each question must have a correct answer of A, B, C or D."
            )

        # Sort question numbers
        self.answer_key = dict(
            sorted(
                self.answer_key.items(),
                key=lambda x: x[0]
            )
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

        # Read with no assumed header, since the official template
        # has an exam-information banner above the real header row
        # (Student ID / Name of the Student / ... / 1 / 2 / 3 ...).
        raw_df = pd.read_excel(
            excel_file,
            sheet_name=sheet_name,
            header=None
        )

        if raw_df.empty:

            raise ValueError(
                "The student response sheet contains no student records."
            )

        header_row_idx = _find_student_response_header(raw_df)

        if header_row_idx is None:

            raise ValueError(
                "Could not find the required header row in the "
                "student response sheet.\n\n"
                "The sheet must contain a student Name column "
                "followed by one column per question, matching "
                "the answer key.\n\n"
                "Download the sample Student Responses template "
                "to see the required layout."
            )

        self.exam_info = _extract_exam_info(
            raw_df,
            header_row_idx
        )

        header_row = raw_df.iloc[header_row_idx]

        df = raw_df.iloc[header_row_idx + 1:].reset_index(drop=True)

        if df.empty:

            raise ValueError(
                "The student response sheet contains no student records."
            )

        # ----------------------------------------------------
        # IDENTIFY ID / NAME / SCORE COLUMNS
        # ----------------------------------------------------

        normalized = {}

        for col in raw_df.columns:

            value = header_row[col]

            if value is None or str(value).strip() == "":
                continue

            key = re.sub(
                r"[\s_\-]+",
                " ",
                str(value).strip().lower()
            )

            if key not in normalized:
                normalized[key] = col

        id_candidates = [
            "student id",
            "studentid",
            "student no",
            "student number",
            "id",
            "roll no",
            "roll number",
            "roll"
        ]

        name_candidates = [
            "name",
            "student name",
            "student"
        ]

        score_candidates = [
            "score",
            "total score",
            "total",
            "marks",
            "total marks",
            "overall score",
            "overall marks"
        ]

        id_col = None
        name_col = None
        score_col = None

        for candidate in id_candidates:

            if candidate in normalized:

                id_col = normalized[candidate]
                break

        for candidate in name_candidates:

            if candidate in normalized:

                name_col = normalized[candidate]
                break

        for candidate in score_candidates:

            if candidate in normalized:

                score_col = normalized[candidate]
                break

        # ----------------------------------------------------
        # FALLBACKS
        # ----------------------------------------------------

        if name_col is None:

            # Look for a column containing "name"
            for col in raw_df.columns:

                value = header_row[col]

                if value is not None and "name" in str(value).lower():

                    name_col = col
                    break

        if id_col is None:

            # Look for roll/student/id
            for col in raw_df.columns:

                value = header_row[col]

                if value is None:
                    continue

                lower = str(value).lower()

                if (
                    "student" in lower
                    or "roll" in lower
                    or lower == "id"
                ):

                    id_col = col
                    break

        if name_col is None:

            raise ValueError(
                "Could not find a student Name column.\n\n"
                "Please include a column such as:\n"
                "Name, Student Name, or Student."
            )

        # ----------------------------------------------------
        # MAP QUESTION COLUMNS
        # ----------------------------------------------------

        question_columns = {}

        for col in raw_df.columns:

            value = header_row[col]

            question_number = normalize_question_label(value)

            if question_number is None:
                continue

            # Only retain questions that exist in answer key
            if question_number in self.answer_key:

                # If duplicate representations exist, first one wins
                if question_number not in question_columns:

                    question_columns[
                        question_number
                    ] = col

        # ----------------------------------------------------
        # CHECK FOR MISSING QUESTIONS
        # ----------------------------------------------------

        missing_questions = [
            number
            for number in self.answer_key
            if number not in question_columns
        ]

        # Missing question columns are allowed because the user
        # may have uploaded incomplete data, but we report them.
        if missing_questions:

            print(
                "Warning: Missing student response columns:",
                missing_questions
            )

        # ----------------------------------------------------
        # BUILD STUDENT DATA
        # ----------------------------------------------------

        student_list = []

        question_numbers = list(
            self.answer_key.keys()
        )

        for row_index, row in df.iterrows():

            # Student ID
            if id_col is not None:

                student_id_value = row[id_col]

                if pd.isna(student_id_value):

                    student_id = str(
                        row_index + 1
                    )

                else:

                    student_id = str(
                        student_id_value
                    ).strip()

            else:

                student_id = str(
                    row_index + 1
                )

            # Name
            name_value = row[name_col]

            if pd.isna(name_value):

                student_name = f"Student {row_index + 1}"

            else:

                student_name = str(
                    name_value
                ).strip()

            # Provided overall score
            provided_score = None

            if score_col is not None:

                score_value = row[score_col]

                if pd.notna(score_value):

                    try:

                        provided_score = float(
                            score_value
                        )

                    except (
                        ValueError,
                        TypeError
                    ):

                        provided_score = None

            # Responses
            responses = []

            for question_number in question_numbers:

                if question_number in question_columns:

                    response_value = row[
                        question_columns[question_number]
                    ]

                    response = normalize_answer(
                        response_value
                    )

                else:

                    response = None

                responses.append(response)

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
                "No student records were found in the response file."
            )

    # ========================================================
    # CALCULATE STUDENT SCORES
    # ========================================================

    def calculate_scores(self):

        if self.student_data is None:

            raise ValueError(
                "Student response data has not been loaded."
            )

        scores = []

        question_numbers = list(
            self.answer_key.keys()
        )

        for responses in self.student_data["responses"]:

            correct = 0

            for index, question_number in enumerate(
                question_numbers
            ):

                if index >= len(responses):
                    continue

                if (
                    responses[index]
                    == self.answer_key[question_number]
                ):

                    correct += 1

            scores.append(correct)

        self.scores = np.array(
            scores,
            dtype=int
        )

        self.student_data["score"] = self.scores

        if self.total_questions > 0:

            self.student_data["percentage"] = np.round(
                self.scores
                / self.total_questions
                * 100,
                2
            )

        else:

            self.student_data["percentage"] = 0.0

    # ========================================================
    # ITEM STATISTICS
    # ========================================================

    def calculate_item_statistics(self):

        if self.scores is None:

            self.calculate_scores()

        if self.total_students == 0:

            return []

        group_size = max(
            1,
            int(
                self.total_students * 0.27
            )
        )

        # ----------------------------------------------------
        # GROUPING SCORE
        #
        # Use provided overall score when available.
        # Otherwise use MCQ score.
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

        upper_group = sorted_indices[
            :group_size
        ]

        lower_group = sorted_indices[
            -group_size:
        ]

        item_stats = []

        question_numbers = list(
            self.answer_key.keys()
        )

        # ====================================================
        # EACH ITEM
        # ====================================================

        for index, question_number in enumerate(
            question_numbers
        ):

            correct_answer = self.answer_key[
                question_number
            ]

            # ------------------------------------------------
            # CORRECT COUNT
            # ------------------------------------------------

            correct_count = 0

            for responses in self.student_data[
                "responses"
            ]:

                if (
                    index < len(responses)
                    and
                    responses[index]
                    == correct_answer
                ):

                    correct_count += 1

            # ------------------------------------------------
            # UPPER GROUP
            # ------------------------------------------------

            upper_correct = 0

            for student_index in upper_group:

                responses = self.student_data.iloc[
                    student_index
                ]["responses"]

                if (
                    index < len(responses)
                    and
                    responses[index]
                    == correct_answer
                ):

                    upper_correct += 1

            # ------------------------------------------------
            # LOWER GROUP
            # ------------------------------------------------

            lower_correct = 0

            for student_index in lower_group:

                responses = self.student_data.iloc[
                    student_index
                ]["responses"]

                if (
                    index < len(responses)
                    and
                    responses[index]
                    == correct_answer
                ):

                    lower_correct += 1

            # ------------------------------------------------
            # DIFFICULTY
            # ------------------------------------------------
            #
            # Status/recommendation logic below always uses the
            # raw (unrounded) value, so rounding to 1 decimal for
            # display never shifts an item across a threshold.

            difficulty_raw = (
                correct_count
                / self.total_students
            )

            difficulty = round(
                difficulty_raw,
                2
            )

            # ------------------------------------------------
            # DISCRIMINATION
            # ------------------------------------------------

            discrimination_raw = (
                upper_correct / group_size
            ) - (
                lower_correct / group_size
            )

            discrimination = round(
                discrimination_raw,
                2
            )

            # ------------------------------------------------
            # DIFFICULTY STATUS
            # ------------------------------------------------

            if difficulty_raw < 0.20:

                difficulty_status = "Very Difficult"

            elif difficulty_raw > 0.80:

                difficulty_status = "Too Easy"

            else:

                difficulty_status = "Ideal"

            # ------------------------------------------------
            # DISCRIMINATION STATUS
            # ------------------------------------------------

            if discrimination_raw < 0:

                discrimination_status = "Negative"

            elif discrimination_raw < 0.20:

                discrimination_status = "Poor"

            elif discrimination_raw < 0.30:

                discrimination_status = "Fair"

            else:

                discrimination_status = "Good"

            # ------------------------------------------------
            # OPTION COUNTS
            # ------------------------------------------------

            option_counts = {
                option: 0
                for option in OPTION_LETTERS
            }

            omitted_count = 0

            for responses in self.student_data[
                "responses"
            ]:

                if index >= len(responses):

                    omitted_count += 1
                    continue

                response = responses[index]

                if response in option_counts:

                    option_counts[
                        response
                    ] += 1

                else:

                    omitted_count += 1

            # ------------------------------------------------
            # DISTRACTOR ANALYSIS
            # ------------------------------------------------

            option_breakdown = []

            non_functional_distractors = []

            distractor_total = 0
            functional_distractor_count = 0

            for option in OPTION_LETTERS:

                count = option_counts[
                    option
                ]

                percentage_raw = (
                    count
                    / self.total_students
                    * 100
                )

                percentage = round(
                    percentage_raw,
                    2
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
                        percentage_raw
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
                        count=int(count),
                        percentage=float(
                            percentage
                        ),
                        is_correct=is_correct,
                        is_functional=is_functional
                    )
                )

            # ------------------------------------------------
            # DISTRACTOR EFFICIENCY
            # ------------------------------------------------

            if distractor_total > 0:

                distractor_efficiency = round(
                    functional_distractor_count
                    / distractor_total
                    * 100,
                    2
                )

            else:

                distractor_efficiency = 0.0

            # ------------------------------------------------
            # OMITTED
            # ------------------------------------------------

            omitted_percentage = round(
                omitted_count
                / self.total_students
                * 100,
                2
            )

            # ------------------------------------------------
            # RECOMMENDATION
            # ------------------------------------------------

            if discrimination_raw < 0:

                recommendation = (
                    ItemRecommendation.DISCARD
                )

            elif (
                discrimination_raw < 0.20
                and
                (
                    difficulty_raw < 0.20
                    or
                    difficulty_raw > 0.80
                )
            ):

                recommendation = (
                    ItemRecommendation.REVISE
                )

            elif (
                discrimination_raw < 0.20
                or
                difficulty_raw < 0.20
                or
                difficulty_raw > 0.80
            ):

                recommendation = (
                    ItemRecommendation.REVIEW
                )

            else:

                recommendation = (
                    ItemRecommendation.RETAIN
                )

            # ------------------------------------------------
            # CREATE ITEM STATS
            # ------------------------------------------------

            item = ItemStats(

                question=f"Question {question_number}",

                question_number=question_number,

                correct_answer=correct_answer,

                correct_count=correct_count,

                total_students=self.total_students,

                difficulty=float(
                    difficulty
                ),

                discrimination=float(
                    discrimination
                ),

                recommendation=recommendation,

                difficulty_status=difficulty_status,

                discrimination_status=(
                    discrimination_status
                ),

                distractor_efficiency=float(
                    distractor_efficiency
                ),

                non_functional_distractors=(
                    non_functional_distractors
                ),

                option_breakdown=(
                    option_breakdown
                ),

                omitted_count=int(
                    omitted_count
                ),

                omitted_percentage=float(
                    omitted_percentage
                )
            )

            item_stats.append(item)

        return item_stats

    # ========================================================
    # RANK STUDENTS
    # ========================================================

    def rank_students(self):

        if self.scores is None:

            self.calculate_scores()

        ranked = self.student_data.copy()

        ranked = ranked.sort_values(
            by=["score", "name"],
            ascending=[False, True]
        )

        stats = []

        previous_score = None
        current_rank = 0

        for position, (_, row) in enumerate(
            ranked.iterrows(),
            start=1
        ):

            score = int(
                row["score"]
            )

            if (
                previous_score is None
                or
                score != previous_score
            ):

                current_rank = position

            stats.append(
                StudentStats(
                    rank=current_rank,

                    student_id=str(
                        row["student_id"]
                    ),

                    name=str(
                        row["name"]
                    ),

                    score=score,

                    percentage=float(
                        row["percentage"]
                    ),

                    responses=row[
                        "responses"
                    ],

                    correct_count=score
                )
            )

            previous_score = score

        return stats

    # ========================================================
    # SUMMARY
    # ========================================================

    def get_summary(self):

        if self.scores is None:

            self.calculate_scores()

        return {
            "total_students": int(
                self.total_students
            ),

            "total_questions": int(
                self.total_questions
            ),

            "mean_score": round(
                float(
                    self.scores.mean()
                ),
                2
            )
            if len(self.scores) > 0
            else 0.0,

            "std_score": round(
                float(
                    self.scores.std()
                ),
                2
            )
            if len(self.scores) > 0
            else 0.0,

            "min_score": int(
                self.scores.min()
            )
            if len(self.scores) > 0
            else 0,

            "max_score": int(
                self.scores.max()
            )
            if len(self.scores) > 0
            else 0,

            "mean_percentage": round(
                float(
                    self.scores.mean()
                    / self.total_questions
                    * 100
                ),
                1
            )
            if (
                len(self.scores) > 0
                and
                self.total_questions > 0
            )
            else 0.0
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
            "students": students,
            "exam_info": self.exam_info
        }
