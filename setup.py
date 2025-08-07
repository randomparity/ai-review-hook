from setuptools import find_packages, setup

setup(
    name="ai-review-hook",
    version="0.1.0",
    description="A pre-commit plugin for AI-assisted code review using OpenAI API",
    author="David Christensen",
    author_email="dave@drc.nz",
    packages=find_packages(),
    install_requires=[
        "openai>=1.0.0",
        "requests",
    ],
    entry_points={
        "console_scripts": [
            "ai-review=ai_review_hook.main:main",
        ],
    },
    python_requires=">=3.7",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
