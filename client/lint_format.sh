flake8 --exclude client/buttonbox_client/ui,resource.py client/buttonbox_client
mypy --strict --exclude resource.py --exclude .+_ui.py --warn-unused-ignore --ignore-missing-imports --follow-imports skip client/buttonbox_client
isort client/buttonbox_client
