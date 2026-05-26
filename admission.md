

# 📘 ADMISSION API DOCUMENTATION (Frontend Guide)

## Base URL

```
/api/admissions/
```

---

# 1.  GET ALL ADMISSIONS (LIST PAGE)

## Endpoint

```
GET /api/admissions/
```

## Supports Filtering

```
/api/admissions/?gender=male
/api/admissions/?religion=christian
/api/admissions/?search=john
/api/admissions/?gender=female&religion=muslim
```

---

## Response (200 OK)

```json id="r1"
[
  {
    "id": 1,
    "first_name": "John",
    "middle_name": "Kofi",
    "surname": "Mensah",
    "date_of_birth": "2015-06-12",
    "gender": "male",
    "religion": "christian",

    "has_normal_health": true,
    "health_condition_details": null,

    "has_normal_hearing": true,
    "hearing_condition_details": null,

    "has_psychological_trauma": false,
    "psychological_trauma_details": null,

    "mother_status": "alive",
    "father_status": "alive",

    "parents_relationship_status": "living_together",

    "fees_payer_name": "Mr. Mensah",
    "fees_payer_phone": "024xxxxxxx",

    "admission_number": "ADM-0001",

    "created_at": "2026-05-26T10:00:00Z"
  }
]
```

---

# 2. GET SINGLE ADMISSION

## Endpoint

```
GET /api/admissions/{id}/
```

## Response (200 OK)

Same structure as above but single object:

```json id="r2"
{
  "id": 1,
  "first_name": "John",
  "surname": "Mensah"
}
```

---

# 3. 📤 CREATE ADMISSION

## Endpoint

```
POST /api/admissions/
```

---

## Request Body

```json id="r3"
{
  "first_name": "Ama",
  "middle_name": "Akosua",
  "surname": "Osei",
  "date_of_birth": "2016-03-20",
  "gender": "female",
  "religion": "christian",

  "has_normal_health": false,
  "health_condition_details": "Asthma",

  "has_normal_hearing": true,
  "hearing_condition_details": null,

  "has_psychological_trauma": false,

  "mother_status": "alive",
  "father_status": "alive",

  "parents_relationship_status": "separated",

  "fees_payer_name": "Mrs. Osei",
  "fees_payer_phone": "020xxxxxxx"
}
```

---

## Response (201 CREATED)

```json id="r4"
{
  "id": 2,
  "first_name": "Ama",
  "surname": "Osei",
  "admission_number": "ADM-0002",
  "created_at": "2026-05-26T11:00:00Z"
}
```

---

# 4. UPDATE ADMISSION

## Endpoint

```
PATCH /api/admissions/{id}/
```

---

## Request

(only fields to update)

```json id="r5"
{
  "fees_payer_phone": "055xxxxxxx"
}
```

---

## Response (200 OK)

Updated object returned.

---

# 5. DELETE ADMISSION

## Endpoint

```
DELETE /api/admissions/{id}/
```

---

## Response (204 NO CONTENT)

```json id="r6"
{}
```

---

# 6. FRONTEND ACTION BUTTONS (IMPORTANT UI RULES)

Each admission row should have:

### 🔘 Buttons:

* ✏️ Edit
* 🗑 Delete
* ✅ Approve
* 🎓 Enrol

---

# 7.  APPROVE ADMISSION (CUSTOM ACTION)

## Endpoint (recommended extension)

```
POST /api/admissions/{id}/approve/
```

## Response

```json id="r7"
{
  "message": "Admission approved",
  "status": "approved"
}
```

---

# 8.  ENROL ADMISSION (VERY IMPORTANT FLOW)

## Frontend Behavior:

When user clicks:

```
🎓 Enrol button
```

### STEP 1:

Fetch admission:

```
GET /api/admissions/{id}/
```

---

### STEP 2:

Open **Add Student Modal**

---

### STEP 3:

Auto-populate fields:

| Student Field  | Admission Source |
| -------------- | ---------------- |
| first_name     | first_name       |
| last_name      | surname          |
| date_of_birth  | date_of_birth    |
| gender         | gender           |
| guardian_name  | fees_payer_name  |
| guardian_phone | fees_payer_phone |
| religion       | religion         |

---

### STEP 4:

Submit to Student API:

```
POST /api/students/
```

---

## Example Student Payload

```json id="r8"
{
  "first_name": "Ama",
  "last_name": "Osei",
  "date_of_birth": "2016-03-20",
  "gender": "female",
  "guardian_name": "Mrs. Osei",
  "guardian_phone": "020xxxxxxx",
  "religion": "christian",
  "admission_id": 2
}
```

---

# 9. VALIDATION ERROR RESPONSE FORMAT

All errors return:

```json id="r9"
{
  "field_name": [
    "Error message here"
  ]
}
```

Example:

```json id="r10"
{
  "health_condition_details": [
    "Health details required."
  ]
}
```

---

# 10. AUTH

All endpoints require:

```
Authorization: Bearer <token>
```

---

# 11. PERMISSIONS

* Only authenticated users can access API
* Only Admin / Headmaster can:

  * create
  * approve
  * delete

---

# 12. 📊 SUMMARY OF ENDPOINTS

| Method | Endpoint                      | Purpose                |
| ------ | ----------------------------- | ---------------------- |
| GET    | /api/admissions/              | list                   |
| GET    | /api/admissions/{id}/         | detail                 |
| POST   | /api/admissions/              | create                 |
| PATCH  | /api/admissions/{id}/         | update                 |
| DELETE | /api/admissions/{id}/         | delete                 |
| POST   | /api/admissions/{id}/approve/ | approve                |
| POST   | /api/students/                | enrol (from admission) |
