#!/usr/bin/env python3
"""
Code quality analysis script for GitHub Actions
"""
import ast
import os
import sys

def main():
    issues = []
    for root, dirs, files in os.walk('.'):
        if '.git' in root or '__pycache__' in root:
            continue
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if 'TODO' in content:
                            issues.append(f'TODO found in {filepath}')
                        if 'FIXME' in content:
                            issues.append(f'FIXME found in {filepath}')
                        if 'print(' in content and 'test' not in filepath.lower():
                            issues.append(f'Debug print statement in {filepath}')
                        try:
                            ast.parse(content)
                        except SyntaxError as e:
                            issues.append(f'Syntax error in {filepath}: {e}')
                except Exception as e:
                    issues.append(f'Error reading {filepath}: {e}')

    if issues:
        print('Quality issues found:')
        for issue in issues:
            print(f'  - {issue}')
        with open('quality-issues.txt', 'w') as f:
            f.write('\n'.join(issues))
    else:
        print('No major quality issues found')

if __name__ == '__main__':
    main()