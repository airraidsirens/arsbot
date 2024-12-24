dbupgrade:
	SQL_VERSION=$$(uv run alembic heads | awk '{print $$1}'); \
	uv run alembic upgrade "$$SQL_VERSION"

.PHONY: migration
migration:
	uv run alembic revision --autogenerate -m "$${message:-change}"
