---
name: python
description: Build backend applications with Python and Flask
license: MIT
---

Check all code with basedpyright, check the lsp configuration files.

Explicitly type python code where the type is ambiguous, like function parameters and return values.

Do not use the `ANY` type, unless specified. For example, `psycopg` returns rows as `tuple[Any, ...]`.

