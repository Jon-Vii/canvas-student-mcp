"""Setup script for Canvas Student MCP."""
from setuptools import setup, find_packages

# Read the contents of requirements.txt
with open("requirements.txt") as f:
    requirements = f.read().splitlines()

# Filter out comments
requirements = [line for line in requirements if not line.strip().startswith('#') and line.strip()]

setup(
    name="canvas-student",
    version="0.1.0",
    description="Canvas Student MCP - Access Canvas LMS through Claude's Model Context Protocol",
    author="Canvas Student MCP Contributors",
    packages=find_packages(),
    install_requires=requirements,
    entry_points={
        'console_scripts': [
            'canvas-mcp=canvas_student.main:main',
        ],
    },
    python_requires='>=3.10',
) 