#!/usr/bin/env python3
"""
Sample Python file for testing the AI review hook.
This file contains some intentional issues for the AI to catch.
"""

def calculate_average(numbers):
    # TODO: This function has a potential division by zero bug
    return sum(numbers) / len(numbers)

def unsafe_eval(user_input):
    # Security issue: using eval() with user input
    return eval(user_input)

class DataProcessor:
    def __init__(self):
        self.data = []
    
    def process_data(self, items):
        # Performance issue: using + in a loop
        result = ""
        for item in items:
            result = result + str(item) + ", "
        return result
    
    def get_item(self, index):
        # No bounds checking - potential IndexError
        return self.data[index]

# Example usage
if __name__ == "__main__":
    processor = DataProcessor()
    numbers = [1, 2, 3, 4, 5]
    
    print(f"Average: {calculate_average(numbers)}")
    print(f"Processed: {processor.process_data(numbers)}")
    
    # This will work
    processor.data = ["a", "b", "c"]
    print(f"Item: {processor.get_item(0)}")
    
    # This could cause an error
    # print(f"Item: {processor.get_item(10)}")
    
    # Dangerous eval usage
    user_code = "2 + 2"
    print(f"Result: {unsafe_eval(user_code)}")
