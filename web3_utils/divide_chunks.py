def divide_chunks(input_list, chunk_size=250):
    return [input_list[i : i + chunk_size] for i in range(0, len(input_list), chunk_size)]
