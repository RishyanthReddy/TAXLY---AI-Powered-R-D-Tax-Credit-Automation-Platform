#!/usr/bin/env python3
"""Script to fix the test_complete_pipeline.py file by removing incorrectly placed test method."""

# Read the file
with open('tests/test_complete_pipeline.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the line with "if __name__"
main_line_index = None
for i, line in enumerate(lines):
    if 'if __name__ == "__main__"' in line:
        main_line_index = i
        break

if main_line_index:
    # Keep only lines up to and including the if __name__ block (5 lines)
    corrected_lines = lines[:main_line_index + 3]  # Keep if __name__, comment, and pytest.main line
    
    # Write back
    with open('tests/test_complete_pipeline.py', 'w', encoding='utf-8') as f:
        f.writelines(corrected_lines)
    
    print(f"Fixed! Removed {len(lines) - len(corrected_lines)} lines")
    print(f"File now has {len(corrected_lines)} lines")
else:
    print("Could not find if __name__ block")
