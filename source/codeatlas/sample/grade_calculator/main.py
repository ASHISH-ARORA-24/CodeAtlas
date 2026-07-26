# Entry point for the grade calculator.
# Imports calculation utilities and the StudentProfile class from utils.py.
# The import line is what creates the graph edge between this file and
# utils.py in the Neo4j knowledge graph.

from utils import calculate_average, calculate_grade, StudentProfile


def get_student_report(name: str, age: int, marks: list[float]) -> dict:
    """
    Builds a complete grade report for a single student.

    Creates a StudentProfile for personal details, then calls
    calculate_average and calculate_grade from utils.py to compute
    the academic result. Assembles everything into a report dictionary.
    """
    profile = StudentProfile(name, age)
    average = calculate_average(marks)
    grade = calculate_grade(average)

    return {
        "profile": profile.get_summary(),
        "marks": marks,
        "average": average,
        "grade": grade,
    }


if __name__ == "__main__":
    # Example usage — run this file directly to see a sample report
    report = get_student_report("Alice", 20, [85, 90, 78, 92, 88])
    print(f"Student : {report['profile']}")
    print(f"Marks   : {report['marks']}")
    print(f"Average : {report['average']}")
    print(f"Grade   : {report['grade']}")
