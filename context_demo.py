#!/usr/bin/env python3
"""
Demo file to show how context-lines affects git diff output.
This file has many lines to demonstrate context.
"""

def function_one():
    """First function in the file."""
    print("This is function one")
    print("Line 2 of function one")
    print("Line 3 of function one")
    return "function_one_result"

def function_two():
    """Second function - this will be modified."""
    print("This is function two")
    print("Line 2 of function two")
    # This line will be changed to demonstrate context
    result = "old_value"
    print("Line 4 of function two")
    print("Line 5 of function two")
    return result

def function_three():
    """Third function in the file."""
    print("This is function three")
    print("Line 2 of function three")
    print("Line 3 of function three")
    return "function_three_result"

def function_four():
    """Fourth function in the file."""
    print("This is function four")
    print("Line 2 of function four")
    print("Line 3 of function four")
    return "function_four_result"

if __name__ == "__main__":
    print("Starting demo")
    result1 = function_one()
    result2 = function_two()
    result3 = function_three()
    result4 = function_four()
    print("Demo completed")
