import re

def parse_log(log_file_path):
    # Define regex patterns
    state_pattern = re.compile(r"State:\s*\(([\d\.,\s]+)\),\s*Region\s*(\d+)")
    answer_pattern = re.compile(r"New Answer:\s*(\d+)")

    # Initialize variables
    state = None
    state_region = None
    new_answer = None
    results = []

    # Read and parse the log file
    with open(log_file_path, 'r') as log_file:
        for line in log_file:
            # Match State and Region
            state_match = state_pattern.search(line)
            if state_match:
                state = tuple(map(float, state_match.group(1).split(',')))
                state_region = int(state_match.group(2))

            # Match New Answer
            answer_match = answer_pattern.search(line)
            if answer_match:
                new_answer = int(answer_match.group(1))
                if state is not None and state_region is not None:
                    results.append([state, state_region, new_answer])
                    # Reset state for the next match
                    state = None
                    state_region = None

    return results

# Example usage
log_file_path = './logging/test_logging_AntMaze_star_LLAMA3_07-10-16-36.log'
parsed_data = parse_log(log_file_path)
for data in parsed_data:
    print(data)
