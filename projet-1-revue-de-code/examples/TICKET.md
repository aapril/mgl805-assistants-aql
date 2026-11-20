# Safe division

As a user of the calculator, I want an understandable error when I divide by zero, so that I can correct my input.

## Acceptance criteria

- AC-1: divide(8, 2) returns 4.
- AC-2: divide(8, 0) raises ValueError with the message "division by zero".
- AC-3: divide(-8, 2) returns -4.

## Constraints

The public signature divide(a, b) stays unchanged. No new dependency.
