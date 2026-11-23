# API conventions

## Success

- Return the result in `data` and set `error` to `null`.
- Use `200` for successful reads and `201` when a resource is created.

## Failure

- Set `data` to `null`.
- Return an error object with `code` and `message`.
- Use `400` for invalid input, `404` for missing resources, and `409` for state conflicts.

Do not expose stack traces, filesystem paths, credentials, or raw upstream errors.

