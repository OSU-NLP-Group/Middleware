import re

def parse_where_clause(where_clause):
    conditions = []

    pattern = re.compile(
        r"([\w\.]*`[^`]+`|\b[\w\.]+\b)\s*(=|<>|!=|>=|<=|<|>|NOT LIKE|LIKE|IS NOT|IS)\s*"
        r"(NULL|TRUE|FALSE|'[^']*'|\"[^\"]*\"|\d+(?:\.\d+)?(?:,\d+)*(?:\.\d+)?)|"
        r"([\w\.]*`[^`]+`|\b[\w\.]+\b)\s+IN\s+\(([^)]+)\)|"
        r"([\w\.]*`[^`]+`|\b[\w\.]+\b)\s+BETWEEN\s+('[^']+?'\s+AND\s+'[^']+?'|\d+\s+AND\s+\d+)|"
        r"([\w\.]*`[^`]+`|\b[\w\.]+\b)\s*=\s*(\(SELECT\s+(?:(?!\)\s*\)).)+\))|"
        # nested math expressions are not supported
        r"\(?([`\w\.]+\s[*\/+-]\s[`\w\.]+)\)?\s*(=|<>|!=|>=|<=|<|>|LIKE)\s*([\d\.]+)|"
        # the remaining patterns are for CAST
        r"\(?([`\w\.\s\(\)-]+[*\/+-]\s*CAST\([`\w\.\s\(\)-]+\sAS\s[A-Z]+\))\)?\s*(=|<>|!=|>=|<=|<|>|LIKE)\s*([\d\.]+)|"
        r"\(?(CAST\([`\w\.\s\(\)-]+\sAS\s[A-Z]+\)\s*[*\/+-]\s*[`\w\.\s\(\)-]+)\)?\s*(=|<>|!=|>=|<=|<|>|LIKE)\s*([\d\.]+)|"
        r"\(?(CAST\([`\w\.\s\(\)-]+\sAS\s[A-Z]+\)\s*[*\/+-]\s*CAST\([`\w\.\s\(\)-]+\sAS\s[A-Z]+\))\)?\s*(=|<>|!=|>=|<=|<|>|LIKE)\s*([\d\.]+)",
        re.IGNORECASE | re.DOTALL
    )



    # Search for patterns and extract conditions
    for match in pattern.finditer(where_clause):
        # BETWEEN condition
        if match.group(6):
            # column = match.group(6).strip("`")
            column = match.group(6)
            values = match.group(7).replace("'", "").split(' AND ')
            conditions.append({
                'column': column,
                'operator': 'BETWEEN',
                'value': values
            })
        # IN condition
        elif match.group(4):
            # column = match.group(4).strip("`")
            column = match.group(4)
            in_values = match.group(5).split(',')
            in_values = [value.strip().strip("'\"") for value in in_values]
            conditions.append({
                'column': column,
                'operator': 'IN',
                'value': in_values
            })
        elif match.group(13):
            # column = match.group(13).strip("`")
            column = match.group(13)
            operator = match.group(14)
            value = match.group(15)
            conditions.append({
                'column': column,
                'operator': operator,
                'value': value
            })
        elif match.group(16):
            # column = match.group(16).strip("`")
            column = match.group(16)
            operator = match.group(17)
            value = match.group(18)
            conditions.append({
                'column': column,
                'operator': operator,
                'value': value
            })
        elif match.group(19):
            # column = match.group(19).strip("`")
            column = match.group(19)
            operator = match.group(20)
            value = match.group(21)
            conditions.append({
                'column': column,
                'operator': operator,
                'value': value
            })
        # Other conditions
        elif match.group(1) or match.group(10):
            # column = match.group(1) if match.group(1) else match.group(10).strip("`")
            column = match.group(1) if match.group(1) else match.group(10)
            operator = match.group(2) if match.group(2) else match.group(11)
            value = match.group(3) if match.group(3) else match.group(12)
            value = value.strip("'\"") if value not in ['NULL', 'TRUE', 'FALSE'] else value
            conditions.append({
                'column': column,
                'operator': operator,
                'value': value
            })
        # Subquery condition
        elif match.group(8):
            # column = match.group(8).strip("`")
            column = match.group(8)
            operator = '='
            # Subquery will be captured, including the SELECT keyword and parentheses
            subquery = match.group(9)
            conditions.append({
                'column': column,
                'operator': operator,
                'value': subquery
            })
        
    return conditions

# Example usage:
test_cases = [
    "`County Name` = 'Alameda'",
    "hehe.`County Name` = 'Alameda'",
    "`FRPM Count (K-12)` = 4419.0",
    "name = 'Alice'",
    "age >= 25",
    "salary <> 5000",
    "date_of_birth < '1995-01-01'",
    "a.bcg = 0.5",
    "`County Name` = 'Alameda'",
    "role IN ('admin', 'user', 'guest')",
    "id IN (1, 2, 3, 4, 5)",
    "date_created BETWEEN '2022-01-01' AND '2022-12-31'",
    "quantity BETWEEN 10 AND 50",
    "email LIKE '%@gmail.com'",
    "username LIKE 'user_%'",
    "address IS NULL",
    "phone IS NOT NULL",
    "first_name = 'John' AND last_name = 'Doe' OR age >= 30 AND status = 'active'",  # to debug
    "price < 100 OR (category = 'electronics' AND stock > 10)",
    "date BETWEEN '2022-01-01' AND '2022-12-31' AND product NOT LIKE '%Pro%' AND manufacturer IS NOT NULL",
    "(satscores.NumGE1500 * 1.0 / satscores.NumTstTakr) > 0.3",
    "satscores.cds IN (SELECT cds FROM satscores ORDER BY NumGE1500 DESC LIMIT 1) AND haha = 3",   # to debug
    "satscores.cds = (SELECT cds FROM satscores ORDER BY NumGE1500 DESC LIMIT 1)",
    "rpm.`FRPM Count (K-12)` = (SELECT MAX(`FRPM Count (K-12)`) FROM frpm)",
    "rpm.`FRPM Count (K-12)` = (SELECT `FRPM Count` FROM frpm)",
    "`Enrollment (K-12)` > 500",
    "schooldata.TotalStudents = (SELECT COUNT(*) FROM students WHERE class IN (SELECT class FROM classes WHERE teacher = 'Smith'))",
    "teacher.name LIKE 'Mr. %' AND (teacher.salary * 1.10 + 3000) IN (SELECT salary FROM salaries WHERE end_date > CURRENT_DATE())",
    "ROUND(school.revenue / school.expense, 2) < 1.5 AND NOT (student.grade < 50 AND student.grade > 0) AND EXISTS (SELECT 1 FROM sports_teams WHERE school_id = school.id AND championships_won > 5)",
    "`Educational Option Type` = 'Continuation School' AND `Free Meal Count (Ages 5-17)` / `Enrollment (Ages 5-17)` IS NOT NULL",
    "T1.`District Name` = 'Fresno County Office of Education' AND T1.`Charter School (Y/N)` = 1",
    "T1.`Charter Funding Type` = 'Directly funded' AND T1.`Charter School (Y/N)` = 1 AND T2.OpenDate > '2000-01-01'",
    "`FRPM Count (K-12)` = (SELECT MAX(`FRPM Count (K-12)`) FROM frpm)",

    # to debug
    "`Grade Low` = '1' AND `Grade High` = '12'",
    "frpm.`Free Meal Count (Ages 5-17)` BETWEEN 1900 AND 2000",
    "schools.County = 'Los Angeles' AND satscores.NumTstTakr BETWEEN 2000 AND 3000",
    "County = 'Fresno' AND OpenDate BETWEEN '1980-01-01' AND '1980-12-31'",
    "cds = (SELECT cds FROM avg_scores ORDER BY AvgScore ASC LIMIT 1)",
    "OpenDate BETWEEN '2000-01-01' AND '2005-12-31' AND County = 'Stanislaus' AND FundingType = 'Directly funded'",
    "StatusType = 'Closed' AND DOCType = 'Community College District' AND County = 'San Francisco' AND ClosedDate BETWEEN '1989-01-01' AND '1989-12-31'",
    "`Educational Option Type` = 'Continuation School'",
    "frpm.`Enrollment (K-12)` > 500",
    "CDSCode IN (SELECT cds FROM satscores WHERE AvgScrMath = 699)",
    "`FRPM Count (K-12)` = (SELECT MAX(`FRPM Count (K-12)`) FROM frpm)",
    "(CAST(satscores.NumGE1500 AS FLOAT) / CAST(satscores.NumTstTakr AS FLOAT)) > 0.3",
    "(satscores.NumGE1500 / satscores.NumTstTakr) > 0.3",

    # to debug
    "NumGE1500 / enroll12 > 0.3",  # this is parsed into enroll12 > 0.3
    "schools.County = 'Alameda' AND satscores.NumTstTakr < 100",
    "(satscores.NumGE1500 / satscores.NumTstTakr) > 0.3",
    "satscores.NumGE1500 / satscores.NumTstTakr > 0.3",
    "satscores.`NumGE1500` / satscores.`NumTstTakr` > 0.3",
    "CDSCode = (SELECT cds FROM satscores ORDER BY NumGE1500 DESC LIMIT 1)",
    "satscores.NumGE1500 / CAST(satscores.NumTstTakr AS FLOAT) > 3 ",
    "CAST(satscores.NumTstTakr AS FLOAT) * satscores.NumGE1500 > 3 ",
    "CAST(T2.`Free Meal Count (K-12)` AS REAL) / T2.`Enrollment (K-12)` > 0.1 AND T1.NumGE1500 > 0",   # to debug
    "CAST(T2.`Free Meal Count` AS REAL) / T2.`Enrollment` > 0.1 AND T1.NumGE1500 > 0",   # to debug
    "(CAST(T2.`Free Meal Count` AS REAL) / T2.`Enrollment`) > 0.1 AND T1.NumGE1500 > 0",   # to debug
     "CAST(T2.`Free Meal Count (K-12)` AS REAL) / T2.`Enrollment` > 0.1 AND T1.NumGE1500 > 0",   # to debug
    "`Percent (%) Eligible Free (K-12)` > 0.1 AND NumGE1500 > 0",
    "(CAST(satscores.NumGE1500 AS REAL) / CAST(satscores.NumTstTakr AS REAL)) > 0.3",
    "(NumGE1500 * 1.0 / NumTstTakr) > 0.3",
    "NumTstTakr > 0 AND CAST(NumGE1500 AS REAL) / CAST(NumTstTakr AS REAL) > 0.3",
    "CDSCode = (SELECT cds FROM satscores ORDER BY NumGE1500 DESC LIMIT 1)"
]

for where_clause in test_cases:
    print(f"Testing: {where_clause}")
    parsed_conditions = parse_where_clause(where_clause)
    print(parsed_conditions)

