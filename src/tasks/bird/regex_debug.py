import re

function_name = "find_columns_containing_value"
input_string = 'find_columns_containing_value("Percent (%) Eligible Free (K-12)")'

# function_name = "is_value_in_column"
# input_string = "is_value_in_column('frpm', 'Percent (%) Eligible Free (K-12)', '0.1')"

# This pattern looks for the function name followed by an opening parenthesis,
# then it lazily matches any characters followed by a closing parenthesis that is not followed by another closing parenthesis.
# The negative lookahead (?![^(]*\)) ensures that we do not stop at a closing parenthesis that has an opening parenthesis before it without a corresponding closing parenthesis in between.
# pattern = r'{}\((.+?(?![^(]*\))\))'.format(re.escape(function_name))
# pattern = r'{}\((.+?)\)'.format(re.escape(function_name))
pattern = r'{}\(((?:[^)(]+|\([^)(]*\))*)\)'.format(re.escape(function_name))


matches = re.findall(pattern, input_string)

print(matches)

