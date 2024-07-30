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

def parse_additional_info(log_file_path):
    # Define regex patterns
    time_pattern = re.compile(r"Time:\s*([\d\.\-]+)")
    partition_count_pattern = re.compile(r"Select Partition Count:\s*(\d+)")
    times_pattern = re.compile(r"Times:\s*(\d+)")
    gpt_input_tokens_pattern = re.compile(r"GPT input tokens:\s*(\d+)")
    gpt_output_tokens_pattern = re.compile(r"GPT output tokens:\s*(\d+)")

    results = []

    # Read and parse the log file
    with open(log_file_path, 'r') as log_file:
        for line in log_file:
            # Match Time
            time_match = time_pattern.search(line)
            if time_match:
                time = float(time_match.group(1))

            # Match Select Partition Count
            partition_count_match = partition_count_pattern.search(line)
            if partition_count_match:
                partition_count = int(partition_count_match.group(1))

            # Match Times
            times_match = times_pattern.search(line)
            if times_match:
                times = int(times_match.group(1))

            # Match GPT input tokens
            gpt_input_tokens_match = gpt_input_tokens_pattern.search(line)
            if gpt_input_tokens_match:
                gpt_input_tokens = int(gpt_input_tokens_match.group(1))

            # Match GPT output tokens
            gpt_output_tokens_match = gpt_output_tokens_pattern.search(line)
            if gpt_output_tokens_match:
                gpt_output_tokens = int(gpt_output_tokens_match.group(1))
                # Append the results to the list once all values are matched
                results.append([time, partition_count, times, gpt_input_tokens, gpt_output_tokens])

    return results

# Example usage
log_file_path = './logging/logging_AntMaze_star_LLAMA3_07-15-17-38.log'
parsed_data = parse_additional_info(log_file_path)
GPT_input_tokens = sum([data[3] for data in parsed_data])
GPT_output_tokens = sum([data[4] for data in parsed_data])
times = sum([data[0] for data in parsed_data])
llm_times = len(parsed_data)

inprice = 5.00 / 1000 / 1000 ### gpt-4o
outprice = 15.00 / 1000 / 1000

# inprice = 0.150/1000/1000 ### gpt-4o-mini
# outprice = 0.600/1000/1000

# Print time in readable format
print(f'Total time: {times // 3600}h {(times % 3600) // 60}m {times % 60}s')
print(f'Total LLAMA times: {llm_times}')
print(f'Avg LLAMA time: {times / llm_times}s')
print(f'Total GPT input tokens: {GPT_input_tokens}')
print(f'Total GPT output tokens: {GPT_output_tokens}')
print(f'Total input price: {GPT_input_tokens * inprice}')
print(f'Total output price: {GPT_output_tokens * outprice}')
print(f'Total price: {GPT_input_tokens * inprice + GPT_output_tokens * outprice}')
