"""
Distribution Testing Suite - Tests That Would Have Caught the Template Bundling Bug

Purpose: Validate the actual package that ships to users, not just development code.

This test category was COMPLETELY MISSING from the original test suite, which allowed
a catastrophic bug to ship through 8+ releases affecting 100% of PyPI users.

Test Philosophy:
- Test what users experience (pip install), not what developers experience (git clone)
- Validate package contents, not just code functionality
- Run without SPEC_KITTY_TEMPLATE_ROOT (simulate real user environment)
- Build → Install → Test workflow

Critical Tests:
1. Package Configuration Validation (pyproject.toml)
2. Package Build and Contents
3. Clean Installation Testing
4. User Experience Simulation
5. Template Content Validation

These tests ensure the package that ships is the package that works.
"""
