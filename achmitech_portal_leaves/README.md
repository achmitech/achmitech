# achmitech_portal_leaves

**Odoo 19 — Portal Leave Approval for Interim Employees**

Adds a client-facing portal workflow for approving or refusing leave requests submitted by interim (temporary) employees assigned to their site.

---

## Context

A recruitment agency places interim employees at client companies. When an interim submits a leave request, their client (the on-site manager) needs to be notified and, for certain leave types, must explicitly approve or refuse the request before it is validated in the system.

---

## Key Concepts

| Term | Meaning |
|---|---|
| **Interim** | Temporary employee placed at a client site |
| **Client** | The on-site manager / company that receives the interim |
| **Client project** | A `project.project` record whose partner is the client; linked to the interim via `client_project_id` on `hr.employee` |
| **Portal user** | Both interims and clients are Odoo portal users (standard `auth="user"` routes) |

---

## Leave Type Modes

| Leave type | Behaviour |
|---|---|
| Sick, Parental | **Notify only** — client receives an informational email; HR continues the standard validation process as usual (client has no action to take) |
| Paid, Unpaid, Compensatory, Extra time off, Extra hours | **Require client approval** — leave is blocked in `client_validate` state until the client approves or refuses |

---

## New Workflow State

```
draft → confirm → client_validate → validate
                        ↓
                      refuse
```

- `client_validate` — *"En attente du client"* — inserted between `confirm` and `validate`
- Client approval is **final**: no additional HR validation step after
- HR managers retain backend override buttons to force-validate or force-refuse without waiting for the client

---

## Module Structure

```
achmitech_portal_leaves/
├── models/
│   ├── hr_employee.py          # Adds client_project_id to employee
│   ├── hr_leave_type.py        # Adds require_client_approval / notify_client_on_confirm / deadline_days
│   └── hr_leave.py             # State machine, actions, notifications, cron
├── controllers/
│   └── portal_leaves.py        # /my/team-leaves/* (client) + /my/leaves/* (interim)
├── views/
│   ├── hr_employee_views.xml
│   ├── hr_leave_type_views.xml
│   ├── hr_leave_views.xml
│   └── portal_leaves_templates.xml
├── data/
│   ├── mail_templates.xml      # 5 email templates
│   └── cron.xml                # Daily reminder cron
├── security/
│   ├── ir.model.access.csv
│   └── security.xml            # Record rules (client + interim)
└── static/
    └── src/img/time_off.svg    # Portal card icon
```

---

## Models

### `hr.employee` — `models/hr_employee.py`

| Field | Type | Description |
|---|---|---|
| `client_project_id` | Many2one → `project.project` | Current mission project; its partner becomes the approving client |

Field is also mirrored on `hr.employee.public` for portal safety.

---

### `hr.leave.type` — `models/hr_leave_type.py`

| Field | Type | Default | Description |
|---|---|---|---|
| `require_client_approval` | Boolean | False | Block leave in `client_validate` until client approves |
| `notify_client_on_confirm` | Boolean | False | Send informational email on submission (no blocking) |
| `client_response_deadline_days` | Integer | 3 | Days before an automated reminder is sent to the client |

---

### `hr.leave` — `models/hr_leave.py`

#### New fields

| Field | Type | Description |
|---|---|---|
| `client_partner_id` | Many2one → `res.partner` (stored, computed) | Derived from `employee_id.client_project_id.partner_id` |
| `client_refuse_reason` | Char | Reason entered by the client when refusing |
| `client_deadline` | Date (stored, computed) | `create_date + client_response_deadline_days` |
| `client_reminded` | Boolean | True once the automatic deadline reminder has been sent |

#### State machine logic

- **`_check_approval_update`** — extended to allow `confirm → client_validate` for all users and to restrict `client_validate → validate/refuse` to `sudo()` context only (portal controller and HR override)
- **`create()`** — intercepts newly confirmed leaves: routes to `client_validate` + sends approval email, or sends notify-only email
- **`action_approve()`** — safety net: any leave still in `confirm` that requires client approval is redirected to `client_validate` instead of being validated directly

#### Action methods

| Method | Called from | Effect |
|---|---|---|
| `action_client_approve()` | Portal (client) | `sudo().with_context(leave_fast_create=True)._action_validate(check_state=False)` then notifies employee |
| `action_client_refuse(reason)` | Portal (client) | Writes `state='refuse'`, stores reason, notifies employee |
| `action_refuse()` | HR backend | Extended to allow refusal from `client_validate` state |
| `action_hr_force_validate()` | HR backend button | Force-validates without client, same sudo+context pattern |
| `action_hr_force_refuse()` | HR backend button | Force-refuses without client |
| `_cron_send_client_leave_reminders()` | Daily cron | Finds overdue `client_validate` leaves, sends reminder, sets `client_reminded=True` |

> **Why `leave_fast_create=True`?**
> Odoo's `hr.leave.write()` checks `self.env.user.has_group(...)` to enforce double-validation rules. This check ignores `sudo()` because it looks at the actual user, not the environment su flag. The `leave_fast_create` context key is Odoo's own bypass mechanism for programmatic state transitions.

---

## Controllers — `controllers/portal_leaves.py`

### Client portal: `/my/team-leaves`

| Route | Method | Description |
|---|---|---|
| `/my/team-leaves` | GET | Leave list with tabs (pending / history), search, sort, groupby, pagination |
| `/my/team-leaves/page/<n>` | GET | Pagination |
| `/my/team-leaves/<id>` | GET | Leave detail with approve / refuse buttons |
| `/my/team-leaves/<id>/approve` | POST | Calls `action_client_approve()`, redirects with flash |
| `/my/team-leaves/<id>/refuse` | POST | Calls `action_client_refuse(reason)`, redirects with flash |

**Access check** — `_check_leave_access(leave_id)` verifies that `client_partner_id` matches the current user's partner; returns HTTP 403 otherwise.

### Interim portal: `/my/leaves`

| Route | Method | Description |
|---|---|---|
| `/my/leaves` | GET | Employee's leave list + "New Leave" modal |
| `/my/leaves/new` | POST | Creates leave; validates `date_to >= date_from` before DB; wraps ORM in `savepoint()` for clean error handling |

**Leave type filter** — Only types with `require_client_approval` or `notify_client_on_confirm` are shown, and only those for which the employee has a valid allocation (computed via `has_valid_allocation` with `employee_id` context).

### Portal home page

- `_prepare_home_portal_values(counters)` — returns `pending_leaves_count` and `my_leaves_count` for the portal counter system
  ⚠️ Non-counter keys must **not** be returned here; the `/my/counters` JSON-RPC endpoint iterates all keys and would cause a `TypeError` if it encounters non-DOM keys, leaving the page spinner permanently visible.
- `home()` override — injects `is_interim`, `is_client`, and `pending_leaves_count` into the template context without touching the counter endpoint.

---

## Views

### `hr_leave_views.xml` — Leave form (HR backend)

- **Status bar** shows `client_validate` stage for both single and double validation workflows
- **HR override buttons** (visible when `state='client_validate'`, group `hr_holidays.group_hr_holidays_manager`):
  - *Forcer la validation* (btn-warning) — with confirm dialog
  - *Forcer le refus* (btn-danger) — with confirm dialog
- **Client info group** (read-only): `client_partner_id`, `client_deadline`, `client_reminded`, `client_refuse_reason`

### `hr_leave_type_views.xml` — Leave type form

- New group *"Approbation client (Intérimaires)"* with the three new fields
- `client_response_deadline_days` is hidden unless `require_client_approval=True`

### `hr_employee_views.xml` — Employee form

- `client_project_id` inserted in the *Work Information* tab

---

## Email Templates — `data/mail_templates.xml`

| Template | Recipient | Trigger |
|---|---|---|
| `mail_template_leave_client_approval` | Client | Leave enters `client_validate` |
| `mail_template_leave_client_notify` | Client | Notify-only leave submitted |
| `mail_template_leave_client_reminder` | Client | Cron: past deadline, not yet reminded |
| `mail_template_leave_approved_by_client` | Employee | Client approves |
| `mail_template_leave_refused_by_client` | Employee | Client refuses (includes reason) |

All templates link back to `/my/team-leaves/<id>` for one-click action.

---

## Security

### `ir.model.access.csv`

| Access | Model | Group | Perms |
|---|---|---|---|
| `access_hr_leave_portal` | `hr.leave` | `base.group_portal` | read only |
| `access_hr_leave_type_portal` | `hr.leave.type` | `base.group_portal` | read only |

### `security.xml` — Record rules (both apply to `base.group_portal`)

| Rule | Domain | Effect |
|---|---|---|
| `hr_leave_rule_portal_client` | `client_partner_id = user.partner_id` | Client sees only leaves of their own interims |
| `hr_leave_rule_portal_interim` | `employee_id.user_id = user` | Interim sees only their own leaves |

Because Odoo ORs record rules within the same group, a user who is both a client and an interim (edge case) sees both sets.

---

## Installation & Configuration

```bash
# Install / upgrade
/usr/bin/odoo -c /etc/odoo/odoo.conf -d odoo19 -u achmitech_portal_leaves \
    --db_host=db --db_port=5432 --db_user=odoo --db_password=odoo --stop-after-init
```

### Setup checklist

1. **Configure leave types** — open each relevant leave type and set:
   - ☑ *Approbation client requise* (for paid/unpaid/compensatory/...)
   - ☑ *Notifier le client à la soumission* (for sick/parental)
   - *Délai de réponse client* (default: 3 days)

2. **Assign client project to interims** — on each interim employee form → *Work Information* tab → set *Projet client (mission actuelle)* to the project whose partner is the client's portal user.

3. **Ensure client has portal access** — the client's `res.partner` must be linked to a portal user (`base.group_portal`).

4. **Verify cron is active** — *Settings → Technical → Automation → Scheduled Actions* → *Absences: rappel client en attente* (runs daily).

---

## Testing

| Scenario | Expected result |
|---|---|
| Interim submits paid leave (require_client_approval=True) | State → `client_validate`; client receives approval email |
| Interim submits sick leave (notify_client_on_confirm=True) | State validates normally; client receives info email only |
| Client visits `/my/team-leaves` | Sees only leaves for their interims |
| Client approves | State → `validate`; employee receives approval email |
| Client refuses with reason | State → `refuse`; employee receives refusal email with reason |
| HR opens `client_validate` leave | Sees override buttons; can force-validate or force-refuse |
| Cron runs past deadline | Client receives reminder; `client_reminded` set to True; no second reminder |
| Interim visits `/my/leaves` | Sees only their own leaves; can submit new requests |
| Interim submits leave with end before start | Flash error shown; no record created |
| Interim submits leave type requiring allocation with no allocation | Flash error shown; no record created |
