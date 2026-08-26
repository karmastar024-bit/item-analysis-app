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
# HELPER FUNCTIONS
# ============================================================

def clean_text(value):
    """
    Normalize a cell/header into a simple comparison string.
    """

    if value is None:
        return ""

    if pd.isna(value):
        return ""

    value = str(value).strip()

    value = re.sub(r"\s+", " ", value)

    return value


def normalize_header(value):
    """
    Normalize a column header for comparison.

    Examples:

        Student Name  -> studentname
        student_name  -> studentname
        Student-ID    -> studentid
        Total Score   -> totalscore
    """

    value = clean_text(value).lower()

    return re.sub(r"[^a-z0-9]", "", value)


# ============================================================
# ROMAN NUMERAL SUPPORT
# ============================================================

ROMAN_VALUES = {
    "i": 1,
    "v": 5,
    "x": 10,
    "l": 50,
    "c": 100,
    "d": 500,
    "m": 1000,
}


def roman_to_int(value):
    """
    Convert a Roman numeral to an integer.

    Examples:

        i   -> 1
        ii  -> 2
        iii -> 3
        iv  -> 4
        v   -> 5
        x   -> 10
    """

    value = value.lower().strip()

    if not value:
        return None

    if not re.fullmatch(r"[ivxlcdm]+", value):
        return None

    total = 0
    previous = 0

    for char in reversed(value):

        current = ROMAN_VALUES.get(char)

        if current is None:
            return None

        if current < previous:
            total -= current
        else:
            total += current

        previous = current

    return total


# ============================================================
# QUESTION LABEL DETECTION
# ============================================================

def detect_question_number(header):
    """
    Detect a question number from many possible header formats.

    Supported examples:

        Q1
        q1
        Q 1
        Q.1
        Q-1
        Q_1
        Question 1
        Question1
        Question No. 1
        Item 1
        Item1
        1
        01
        Qi
        Qii
        Qiii
        Qiv
        Qv
        Qx

    Returns:
        integer question number
        or None if the header does not look like a question.
    """

    original = clean_text(header)

    if not original:
        return None

    value = original.lower().strip()

    # --------------------------------------------------------
    # Numeric-only headers
    # --------------------------------------------------------

    if re.fullmatch(r"\d+", value):

        try:
            number = int(value)

            if number > 0:
                return number

        except ValueError:
            pass

    # --------------------------------------------------------
    # Question / Item + number
    # --------------------------------------------------------

    patterns = [

        # Question No. 1
        r"^question\s*(?:no|number)?\.?\s*(\d+)$",

        # Question1
        r"^question\s*(\d+)$",

        # Item 1
        r"^item\s*(?:no|number)?\.?\s*(\d+)$",

        # Q1 / Q 1 / Q.1 / Q-1 / Q_1
        r"^q[\s._-]*(\d+)$",

    ]

    for pattern in patterns:

        match = re.match(pattern, value, re.IGNORECASE)

        if match:

            number = int(match.group(1))

            if number > 0:
                return number

    # --------------------------------------------------------
    # Roman numeral forms
    #
    # Qi
    # Qii
    # Qiii
    # Qiv
    # Qv
    # Qvi
    # Qvii
    # Qviii
    # Qix
    # Qx
    # --------------------------------------------------------

    roman_match = re.match(
        r"^q[\s._-]*([ivxlcdm]+)$",
        value,
        re.IGNORECASE
    )

    if roman_match:

        roman_value = roman_match.group(1)

        number = roman_to_int(roman_value)

        if number is not None and number > 0:
            return number

    # --------------------------------------------------------
    # Question + Roman numeral
    #
    # Question i
    # Question ii
    # --------------------------------------------------------

    roman_question_match = re.match(
        r"^question\s*([ivxlcdm]+)$",
        value,
        re.IGNORECASE
    )

    if roman_question_match:

        number = roman_to_int(
            roman_question_match.group(1)
        )

        if number is not None and number > 0:
            return number

    return None


def normalize_question_label(header):
    """
    Convert any recognized question header into:

        Q1
        Q2
        Q3
        ...

    Returns None if it cannot be identified.
    """

    number = detect_question_number(header)

    if number is None:
        return None

    return f"Q{number}"


# ============================================================
# COLUMN DETECTION
# ============================================================

def find_column(df, aliases):
    """
    Find a column using a list of possible names.

    Matching ignores:

        spaces
        punctuation
        capitalization
        underscores
        hyphens
    """

    normalized_columns = {
        normalize_header(column): column
        for column in df.columns
    }

    for alias in aliases:

        normalized_alias = normalize_header(alias)

        if normalized_alias in normalized_columns:

            return normalized_columns[normalized_alias]

    return None


def detect_name_column(df):
    """
    Detect student-name column.
    """

    aliases = [
        "Name",
        "Student Name",
        "Student_Name",
        "Student",
        "Candidate",
        "Candidate Name",
        "Learner",
        "Learner Name",
        "Pupil",
        "Pupil Name",
    ]

    return find_column(df, aliases)


def detect_id_column(df):
    """
    Detect student identifier / roll number column.
    """

    aliases = [
        "Student ID",
        "StudentID",
        "ID",
        "Roll",
        "Roll No",
        "Roll Number",
        "Roll_No",
        "Roll_No.",
        "Index",
        "Index No",
        "Index Number",
        "Candidate No",
        "Candidate Number",
        "Admission No",
        "Admission Number",
    ]

    return find_column(df, aliases)


def detect_score_column(df):
    """
    Detect an overall/provided score column.

    This score is used to rank students for the
    upper/lower discrimination groups.
    """

    aliases = [
        "Score",
        "Total Score",
        "TotalScore",
        "Total",
        "Marks",
        "Total Marks",
        "TotalMarks",
        "Overall Score",
        "OverallScore",
        "Overall Marks",
        "OverallMarks",
        "Final Score",
        "FinalScore",
        "Final Marks",
        "FinalMarks",
    ]

    return find_column(df, aliases)


# ============================================================
# QUESTION COLUMN DETECTION
# ============================================================

def detect_question_columns(df):
    """
    Detect every column that looks like a question.

    Returns:

        {
            "Q1": original_column_name,
            "Q2": original_column_name,
            ...
        }

    The returned dictionary is automatically sorted numerically.
    """

    question_columns = {}

    for column in df.columns:

        normalized = normalize_question_label(column)

        if normalized is None:
            continue

        if normalized in question_columns:

            raise ValueError(
                f"Duplicate question detected: {normalized}. "
                f"More than one column appears to represent "
                f"{normalized}."
            )

        question_columns[normalized] = column

    # Sort Q1, Q2, Q3...
    question_columns = dict(
        sorted(
            question_columns.items(),
            key=lambda x: int(x[0][1:])
        )
    )

    return question_columns


# ============================================================
# ANSWER NORMALIZATION
# ============================================================

def normalize_answer(value):
    """
    Normalize an answer cell.

    Accepts:

        A
        a
        A.
        B
        b
        etc.

    Returns:

        A / B / C / D
        or None
    """

    if value is None or pd.isna(value):
        return None

    value = str(value).strip().upper()

    # Remove punctuation around answer
    value = re.sub(r"[^A-Z]", "", value)

    if value in OPTION_LETTERS:
        return value

    return None


# ============================================================
# MAIN ANALYZER
# ============================================================

class ItemAnalyzer:

    def __init__(self):

        self.answer_key = {}

        self.student_data = None

        self.scores = None

        self.total_students = 0

        self.total_questions = 0

        self.question_columns = {}

        self.student_name_column = None

        self.student_id_column = None

        self.student_score_column = None


    # ========================================================
    # LOAD ANSWER KEY
    # ========================================================

    def load_answer_key(self, excel_file):
        """
        Load answer key using flexible question detection.

        Supported formats include:

            Q1 | Q2 | Q3
            D  | B  | C

        or:

            Question 1 | Question 2 | Question 3
            D          | B          | C

        or:

            1 | 2 | 3
            D | B | C

        or:

            Qi | Qii | Qiii
            D  | B   | C
        """

        xl_file = pd.ExcelFile(excel_file)

        if not xl_file.sheet_names:

            raise ValueError(
                "The answer-key workbook contains no worksheets."
            )

        sheet_name = xl_file.sheet_names[0]

        df = pd.read_excel(
            excel_file,
            sheet_name=sheet_name,
            header=0
        )

        if df.empty:

            raise ValueError(
                "Answer key sheet contains no data."
            )

        # ----------------------------------------------------
        # Detect question columns
        # ----------------------------------------------------

        detected_questions = detect_question_columns(df)

        if not detected_questions:

            raise ValueError(
                "No question columns were detected in the answer key.\n\n"
                "Examples of supported question labels are:\n"
                "Q1, q1, Q 1, Question 1, Item 1, 1, Qi, Qii..."
            )

        # ----------------------------------------------------
        # Read answer from first data row
        # ----------------------------------------------------

        answer_row = df.iloc[0]

        answer_key = {}

        invalid_questions = []

        for normalized_question, original_column in detected_questions.items():

            answer = normalize_answer(
                answer_row[original_column]
            )

            if answer is None:

                invalid_questions.append(
                    f"{original_column} = "
                    f"{answer_row[original_column]}"
                )

                continue

            answer_key[
                normalized_question
            ] = answer

        if invalid_questions:

            raise ValueError(
                "The following answer-key entries are invalid:\n\n"
                + "\n".join(invalid_questions)
                + "\n\nAnswers must be A, B, C, or D."
            )

        self.answer_key = answer_key

        self.total_questions = len(answer_key)

        if self.total_questions == 0:

            raise ValueError(
                "No valid answer-key questions were found."
            )

        print(
            f"✓ Answer key loaded: "
            f"{self.total_questions} questions"
        )

        for question, answer in self.answer_key.items():

            print(
                f"  {question}: {answer}"
            )


    # ========================================================
    # LOAD STUDENT RESPONSES
    # ========================================================

    def load_student_responses(self, excel_file):
        """
        Load student response data using flexible detection.

        The question columns do NOT have to use the same
        names as the answer key.

        Example:

            Answer key:
                Q1 Q2 Q3

            Student data:
                1  2  3

        Both become:

            Q1 Q2 Q3
        """

        if self.total_questions == 0:

            raise ValueError(
                "Load the answer key before loading student responses."
            )

        xl_file = pd.ExcelFile(excel_file)

        if not xl_file.sheet_names:

            raise ValueError(
                "The student-response workbook contains no worksheets."
            )

        sheet_name = xl_file.sheet_names[0]

        df = pd.read_excel(
            excel_file,
            sheet_name=sheet_name,
            header=0
        )

        if df.empty:

            raise ValueError(
                "Student response sheet contains no data."
            )

        # ----------------------------------------------------
        # Detect student fields
        # ----------------------------------------------------

        name_col = detect_name_column(df)

        id_col = detect_id_column(df)

        score_col = detect_score_column(df)

        # ----------------------------------------------------
        # Name is essential
        # ----------------------------------------------------

        if name_col is None:

            raise ValueError(
                "Could not identify the student-name column.\n\n"
                "Please use a header such as:\n"
                "Name, Student Name, Student, Candidate, or Learner."
            )

        # ----------------------------------------------------
        # ID is optional
        #
        # If there is no ID column, create one automatically.
        # ----------------------------------------------------

        if id_col is None:

            print(
                "⚠ No student ID/Roll column detected. "
                "Generating sequential student IDs."
            )

        # ----------------------------------------------------
        # Detect question columns
        # ----------------------------------------------------

        detected_questions = detect_question_columns(df)

        if not detected_questions:

            raise ValueError(
                "No question columns were detected in the "
                "student-response file.\n\n"
                "Supported examples:\n"
                "Q1, q1, Question 1, Item 1, 1, Qi, Qii..."
            )

        self.question_columns = detected_questions

        print(
            f"✓ Detected {len(detected_questions)} "
            f"question columns in student data."
        )

        # ----------------------------------------------------
        # Make sure every answer-key question exists
        # ----------------------------------------------------

        missing_questions = [
            q
            for q in self.answer_key
            if q not in detected_questions
        ]

        if missing_questions:

            raise ValueError(
                "The student-response file is missing "
                "the following question(s):\n\n"
                + ", ".join(missing_questions)
            )

        # ----------------------------------------------------
        # Ignore extra questions that aren't in answer key
        # ----------------------------------------------------

        extra_questions = [
            q
            for q in detected_questions
            if q not in self.answer_key
        ]

        if extra_questions:

            print(
                "⚠ Extra question columns detected and ignored: "
                + ", ".join(extra_questions)
            )

        # ----------------------------------------------------
        # Store detected fields
        # ----------------------------------------------------

        self.student_name_column = name_col

        self.student_id_column = id_col

        self.student_score_column = score_col

        if score_col is None:

            print(
                "⚠ No overall Score column detected. "
                "MCQ score will be used for ranking."
            )

        # ----------------------------------------------------
        # Build student records
        # ----------------------------------------------------

        student_list = []

        question_labels = list(
            self.answer_key.keys()
        )

        for row_index, row in df.iterrows():

            # -----------------------------------------------
            # Student ID
            # -----------------------------------------------

            if id_col is not None:

                raw_id = row[id_col]

                if pd.isna(raw_id):

                    student_id = str(
                        row_index + 1
                    )

                else:

                    student_id = clean_text(raw_id)

            else:

                student_id = str(
                    row_index + 1
                )

            # -----------------------------------------------
            # Student name
            # -----------------------------------------------

            raw_name = row[name_col]

            if pd.isna(raw_name):

                student_name = f"Student {row_index + 1}"

            else:

                student_name = clean_text(
                    raw_name
                )

            # -----------------------------------------------
            # Provided score
            # -----------------------------------------------

            provided_score = None

            if score_col is not None:

                raw_score = row[score_col]

                if pd.notna(raw_score):

                    try:

                        provided_score = float(
                            raw_score
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

            for question in question_labels:

                original_column = detected_questions[
                    question
                ]

                raw_response = row[
                    original_column
                ]

                response = normalize_answer(
                    raw_response
                )

                responses.append(
                    response
                )

            student_list.append({

                "student_id":
                    student_id,

                "name":
                    student_name,

                "responses":
                    responses,

                "provided_score":
                    provided_score,

            })

        self.student_data = pd.DataFrame(
            student_list
        )

        self.total_students = len(
            self.student_data
        )

        if self.total_students == 0:

            raise ValueError(
                "No student records were found."
            )

        print(
            f"✓ Loaded {self.total_students} students."
        )


    # ========================================================
    # CALCULATE MCQ SCORES
    # ========================================================

    def calculate_scores(self):

        scores = []

        question_labels = list(
            self.answer_key.keys()
        )

        for responses in self.student_data[
            "responses"
        ]:

            correct = 0

            for index, question in enumerate(
                question_labels
            ):

                if index >= len(responses):
                    continue

                if (
                    responses[index]
                    == self.answer_key[question]
                ):

                    correct += 1

            scores.append(correct)

        self.scores = np.array(
            scores,
            dtype=float
        )

        self.student_data["score"] = (
            self.scores
        )

        self.student_data["percentage"] = (
            self.scores
            / self.total_questions
            * 100
        )

        print(
            f"✓ MCQ scores calculated. "
            f"Mean = {self.scores.mean():.2f}"
        )


    # ========================================================
    # ITEM STATISTICS
    # ========================================================

    def calculate_item_statistics(self):

        if self.total_students == 0:

            return []

        # ----------------------------------------------------
        # 27% upper/lower group
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
            and self.student_data[
                "provided_score"
            ].notna().all()
        ):

            grouping_scores = (
                self.student_data[
                    "provided_score"
                ].to_numpy()
            )

            print(
                "Using provided overall Score "
                "for upper/lower grouping."
            )

        else:

            grouping_scores = (
                self.scores
            )

            print(
                "Using calculated MCQ score "
                "for upper/lower grouping."
            )

        # ----------------------------------------------------
        # Sort students
        # ----------------------------------------------------

        sorted_indices = np.argsort(
            -grouping_scores
        )

        upper_group = sorted_indices[
            :group_size
        ]

        lower_group = sorted_indices[
            -group_size:
        ]

        # ----------------------------------------------------
        # Calculate each item
        # ----------------------------------------------------

        item_stats = []

        question_labels = list(
            self.answer_key.keys()
        )

        for q_idx, question in enumerate(
            question_labels
        ):

            correct_answer = (
                self.answer_key[question]
            )

            # ------------------------------------------------
            # Correct responses
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

                responses = self.student_data.iloc[
                    student_index
                ]["responses"]

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

                responses = self.student_data.iloc[
                    student_index
                ]["responses"]

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
                upper_correct
                / group_size
                -
                lower_correct
                / group_size
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

            elif discrimination < 0.30:

                discrimination_status = (
                    "Fair"
                )

            elif discrimination < 0.40:

                discrimination_status = (
                    "Good"
                )

            else:

                discrimination_status = (
                    "Very Good"
                )

            # ------------------------------------------------
            # Option distribution
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

            # ------------------------------------------------
            # Distractor analysis
            # ------------------------------------------------

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
                    / self.total_students
                    * 100
                )

                is_correct = (
                    option
                    == correct_answer
                )

                # Correct answer isn't a distractor
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

                        is_functional=is_functional,

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

                distractor_efficiency = 0.0

            # ------------------------------------------------
            # Omitted percentage
            # ------------------------------------------------

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

            elif discrimination < 0.20 and (
                difficulty < 0.20
                or difficulty > 0.80
            ):

                recommendation = (
                    ItemRecommendation.REVISE
                )

            elif discrimination < 0.20 or (
                difficulty < 0.20
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
            # Store statistics
            # ------------------------------------------------

            stat = ItemStats(

                question=question,

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

                option_breakdown=(
                    option_breakdown
                ),

                omitted_count=omitted_count,

                omitted_percentage=(
                    omitted_percentage
                ),

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
            "rank"
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
                    ),

                )
            )

        return stats


    # ========================================================
    # SUMMARY
    # ========================================================

    def get_summary(self):

        return {

            "total_students":
                self.total_students,

            "total_questions":
                self.total_questions,

            "mean_score":
                float(
                    self.scores.mean()
                )
                if len(self.scores) > 0
                else 0,

            "std_score":
                float(
                    self.scores.std()
                )
                if len(self.scores) > 0
                else 0,

            "min_score":
                int(
                    self.scores.min()
                )
                if len(self.scores) > 0
                else 0,

            "max_score":
                int(
                    self.scores.max()
                )
                if len(self.scores) > 0
                else 0,

            "mean_percentage":
                float(
                    self.scores.mean()
                    / self.total_questions
                    * 100
                )
                if (
                    len(self.scores) > 0
                    and self.total_questions > 0
                )
                else 0,

            "pass_rate":
                float(
                    (
                        sum(
                            self.scores >= 50
                        )
                        / self.total_students
                        * 100
                    )
                )
                if self.total_students > 0
                else 0,

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
            "\n=== Starting Flexible Item Analysis ==="
        )

        # ----------------------------------------------------
        # 1. Load answer key
        # ----------------------------------------------------

        self.load_answer_key(
            answer_key_file
        )

        # ----------------------------------------------------
        # 2. Load student responses
        # ----------------------------------------------------

        self.load_student_responses(
            student_data_file
        )

        # ----------------------------------------------------
        # 3. Calculate student scores
        # ----------------------------------------------------

        self.calculate_scores()

        # ----------------------------------------------------
        # 4. Calculate item statistics
        # ----------------------------------------------------

        items = (
            self.calculate_item_statistics()
        )

        # ----------------------------------------------------
        # 5. Rank students
        # ----------------------------------------------------

        students = (
            self.rank_students()
        )

        # ----------------------------------------------------
        # 6. Summary
        # ----------------------------------------------------

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
                students,

        }
