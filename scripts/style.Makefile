PHONY += fix-whitespace-last-commit
fix-whitespace-last-commit:
	$(Q)git diff --name-only --diff-filter=M HEAD~1..HEAD | xargs -r python3 scripts/fix_whitespace_issues.py

PHONY += style
style:
	$(Q)if which black > /dev/null ; then black . || true; fi
	$(Q)python3 scripts/detect_whitespace_issues.py || true
	$(Q)python3 scripts/detect_indentation_issues.py || true
	$(Q)python3 scripts/check_commit_format.py || true
	$(Q)python3 scripts/ensure_newlines.py || true

