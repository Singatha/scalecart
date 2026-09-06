# User-service contract

The user service owns customer identity, authentication, profiles, roles, and delivery addresses.
Public requests pass through the gateway under `/api`; the service itself exposes the paths below
without that prefix.

## Authentication

Register with an email, a password of 12–128 characters containing uppercase, lowercase, and numeric
characters, and the customer's name:

```http
POST /api/auth/register
Content-Type: application/json

{
  "email": "ada@example.com",
  "password": "CorrectHorse9",
  "first_name": "Ada",
  "last_name": "Lovelace"
}
```

Registration and `POST /api/auth/login` return the profile plus a bearer access token and refresh
token. Send the access token as `Authorization: Bearer <token>`. Access tokens default to 15 minutes;
refresh tokens default to seven days.

`POST /api/auth/refresh` accepts `{ "refresh_token": "..." }` and returns a new pair. Rotation is
one-time: the submitted refresh token is atomically revoked and replay returns `401`. Logout accepts
the same body and revokes that token. Only SHA-256 token digests—not usable refresh tokens—are stored.

## Profiles and addresses

`GET /api/users/me` returns the current profile and role names. `PATCH /api/users/me` accepts any of
`first_name`, `last_name`, and `phone`.

Addresses are available at `/api/users/me/addresses`. A create request contains:

```json
{
  "label": "Home",
  "recipient_name": "Ada Lovelace",
  "line1": "12 Computing Lane",
  "line2": null,
  "city": "Cape Town",
  "region": "Western Cape",
  "postal_code": "8001",
  "country_code": "ZA",
  "phone": null,
  "is_default": true
}
```

The first address becomes the default automatically. Selecting another default clears the old one.
Deleting the default promotes the oldest remaining address. Address lookups include the authenticated
user ID in the query, so another customer's address is returned as `404` rather than disclosed.

## Roles and bootstrap

Migration `0002_user_domain` creates `customer` and `admin` roles. New registrations receive
`customer`. An administrator can inspect `GET /api/users/{user_id}` and replace roles with
`PUT /api/users/{user_id}/roles` using `{ "roles": ["customer", "admin"] }`.

For the first administrator, configure `BOOTSTRAP_ADMIN_EMAIL` and `BOOTSTRAP_ADMIN_PASSWORD`, run
the migrations, then run `make seed`. Seeding creates the account with both roles or adds missing roles
to an existing account; it never resets an existing password.
