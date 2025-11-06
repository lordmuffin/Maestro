#!/usr/bin/env python3
"""
Simple standalone test script to verify file reading functionality
"""
import os
from typing import List

def read_prompts_from_file(file_path: str) -> List[str]:
    """
    Read prompts from a .md or .txt file.
    Supports multiple prompts separated by '---' on its own line.
    """
    # Check file extension
    if not (file_path.endswith('.md') or file_path.endswith('.txt')):
        raise ValueError(f"Prompt file must be .md or .txt, got: {file_path}")

    # Check if file exists
    if not os.path.exists(file_path):
        raise ValueError(f"Prompt file not found: {file_path}")

    # Read file content
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split by --- separator (on its own line)
    prompts = []
    parts = content.split('\n---\n')

    for part in parts:
        # Strip leading/trailing whitespace
        prompt = part.strip()
        if prompt:  # Only add non-empty prompts
            prompts.append(prompt)

    if not prompts:
        raise ValueError(f"No prompts found in file: {file_path}")

    return prompts


def test_read_md_file():
    """Test reading .md file with multiple prompts"""
    print("Testing read_prompts_from_file with .md file...")
    try:
        prompts = read_prompts_from_file('test_prompts_a.md')
        print(f"✓ Successfully read {len(prompts)} prompts from test_prompts_a.md")
        for i, prompt in enumerate(prompts, 1):
            print(f"  Prompt {i}: {prompt[:60]}...")
        assert len(prompts) == 3, f"Expected 3 prompts, got {len(prompts)}"
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_read_txt_file():
    """Test reading .txt file with multiple prompts"""
    print("\nTesting read_prompts_from_file with .txt file...")
    try:
        prompts = read_prompts_from_file('test_prompts_b.txt')
        print(f"✓ Successfully read {len(prompts)} prompts from test_prompts_b.txt")
        for i, prompt in enumerate(prompts, 1):
            print(f"  Prompt {i}: {prompt[:60]}...")
        assert len(prompts) == 2, f"Expected 2 prompts, got {len(prompts)}"
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_invalid_extension():
    """Test that invalid extensions are rejected"""
    print("\nTesting invalid file extension...")
    try:
        prompts = read_prompts_from_file('test.pdf')
        print("✗ Should have raised ValueError for .pdf file")
        return False
    except ValueError as e:
        print(f"✓ Correctly rejected invalid extension: {e}")
        return True
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

def test_nonexistent_file():
    """Test that nonexistent files are handled"""
    print("\nTesting nonexistent file...")
    try:
        prompts = read_prompts_from_file('nonexistent.md')
        print("✗ Should have raised ValueError for nonexistent file")
        return False
    except ValueError as e:
        print(f"✓ Correctly handled nonexistent file: {e}")
        return True
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("File Reading Test Suite (Standalone)")
    print("=" * 60)

    results = [
        test_read_md_file(),
        test_read_txt_file(),
        test_invalid_extension(),
        test_nonexistent_file()
    ]

    print("\n" + "=" * 60)
    print(f"Results: {sum(results)}/{len(results)} tests passed")
    print("=" * 60)

    if all(results):
        print("\n✓ All tests passed! File reading functionality is working correctly.")
    else:
        print("\n✗ Some tests failed. Please check the errors above.")
