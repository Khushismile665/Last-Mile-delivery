# Last-Mile Delivery Tracker Platform

A logistics operations platform with dynamic rate calculation, automatic zone detection, intelligent delivery agent auto-assignment, immutable tracking history, failed delivery rescheduling workflows, and role-based access control for Admins, Customers, and Delivery Agents.

---

## 🌟 Key Features

### 1. Role-Based Access Control (RBAC)

* **Customer**

  * Create delivery orders
  * View real-time itemized price estimates
  * Track delivery status and timeline
  * Reschedule failed deliveries

* **Delivery Agent**

  * View assigned delivery tasks
  * Toggle availability
  * Update current location
  * Update delivery status
  * Mark deliveries as failed with a mandatory failure reason

* **Admin**

  * Manage delivery zones and pincodes
  * Configure B2B/B2C rate cards
  * Configure COD surcharges
  * View and filter all orders
  * Manually assign delivery agents
  * Trigger automatic agent assignment
  * Override order statuses
  * View notification and audit logs

### 2. Dynamic Rate Calculation Engine

The platform dynamically calculates delivery charges using:

* Actual package weight
* Volumetric weight
* Billable weight
* Pickup and drop zones
* Intra-zone/inter-zone route classification
* B2B/B2C rate cards
* COD surcharges
* Minimum applicable charges

### 3. Intelligent Auto-Assignment

Delivery agents are ranked using a composite scoring algorithm based on:

* Haversine geographical distance
* Active zone matching
* Current workload
* Agent availability

The agent with the lowest composite score is automatically selected.

### 4. Failed Delivery & Rescheduling

When a delivery fails:

1. Failure reason is captured.
2. Customer is notified.
3. Failure is recorded in the tracking history.
4. Customer selects a new delivery date/time slot.
5. Order is marked `RESCHEDULED`.
6. The auto-assignment engine is triggered again.

### 5. Immutable Tracking Timeline

Every order status transition creates a tracking history record containing:

* Status
* Timestamp
* Actor ID
* Actor role
* Location coordinates
* Operational notes

---

# 🚀 Quick Setup

## Prerequisites

* Python 3.9+
* Python 3.13 supported
* Git
* pip

## 1. Clone the Repository

```bash
git clone https://github.com/Khushismile665/Last-Mile-delivery.git
cd Last-Mile-delivery
```

## 2. Create a Virtual Environment

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### Linux/macOS

```bash
python3 -m venv venv
source venv/bin/activate
```

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

## 4. Configure Environment Variables

Create a `.env` file based on `.env.example`.

```bash
copy .env.example .env
```

Configure the required application settings inside `.env`.

> Never commit passwords, API keys, JWT secrets, or other sensitive credentials to GitHub.

## 5. Run the Application

```bash
python run.py
```

The application initializes the database, seeds demo data, and starts the web server.

Open:

```text
http://127.0.0.1:8000
```

---

# 🔑 Demo Login Credentials

| Role     | Email                  | Password       |
| -------- | ---------------------- | -------------- |
| Admin    | `admin@delivery.com`   | `Admin@123`    |
| Customer | `customer@example.com` | `Customer@123` |
| Agent    | `agent1@delivery.com`  | `Agent@123`    |

> These credentials are intended for local/demo evaluation only. Change or remove seeded credentials before production deployment.

---

# 📂 Project Structure

```text
Last-Mile-delivery/
│
├── app/
│   ├── config.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── rate_engine.py
│   ├── assignment_engine.py
│   ├── notification_engine.py
│   ├── seed.py
│   ├── main.py
│   │
│   └── routers/
│       ├── auth.py
│       ├── zones.py
│       ├── rates.py
│       ├── orders.py
│       └── agents.py
│
├── templates/
│   └── index.html
│
├── static/
│   ├── app.js
│   └── style.css
│
├── test_system.py
├── run.py
├── SYSTEM_DESIGN.md
├── README.md
├── requirements.txt
├── Procfile
├── render.yaml
├── vercel.json
├── Dockerfile
└── .env.example
```

---

# 🌐 API Documentation

## Authentication

### Register

```http
POST /api/auth/register
```

Registers a new user account.

Supported roles:

```text
CUSTOMER
AGENT
ADMIN
```

### Login

```http
POST /api/auth/login
```

Authenticates a user and returns a JWT access token.

### Current User

```http
GET /api/auth/me
```

Returns the profile of the currently authenticated user.

---

# 💰 Rate Calculation APIs

### Calculate Delivery Price

```http
POST /api/rates/calculate
```

Calculates the estimated delivery price using package dimensions, weight, zones, order type, and payment type.

### Get Rate Cards

```http
GET /api/rates/cards
```

Returns configured delivery rate cards.

### Create/Update Rate Card

```http
POST /api/rates/cards
```

Admin-only endpoint for configuring B2B/B2C and intra/inter-zone pricing.

### Get COD Surcharges

```http
GET /api/rates/cod
```

Returns configured COD surcharge rules.

### Create/Update COD Surcharge

```http
POST /api/rates/cod
```

Admin-only endpoint for configuring COD fees.

---

# 📍 Zone Management APIs

### Get Zones

```http
GET /api/zones
```

Returns all configured delivery zones and their mapped pincodes.

### Create Zone

```http
POST /api/zones
```

Admin-only endpoint for creating a delivery zone.

### Add Area/Pincode

```http
POST /api/zones/{zone_id}/areas
```

Adds a pincode and area mapping to a zone.

### Delete Area Mapping

```http
DELETE /api/zones/areas/{area_id}
```

Removes an existing area mapping.

---

# 📦 Orders & Tracking APIs

### Create Order

```http
POST /api/orders
```

Creates a new delivery order.

The system automatically:

1. Resolves pickup and drop zones.
2. Calculates volumetric weight.
3. Determines billable weight.
4. Determines the route type.
5. Calculates the delivery charge.
6. Applies COD surcharge when applicable.
7. Creates the order.
8. Generates the initial tracking history.
9. Triggers agent auto-assignment.

### Get Orders

```http
GET /api/orders
```

Returns orders available to the authenticated user based on their role.

Customers see their own orders, agents see assigned orders, and administrators can access all orders.

### Get Order Details

```http
GET /api/orders/{order_id}
```

Returns complete information about a specific order.

### Update Order Status

```http
PATCH /api/orders/{order_id}/status
```

Updates the delivery status.

Supported statuses include:

```text
CREATED
ASSIGNED
PICKED_UP
IN_TRANSIT
OUT_FOR_DELIVERY
DELIVERED
FAILED
RESCHEDULED
```

When the status is `FAILED`, a failure reason is mandatory.

### Get Tracking History

```http
GET /api/orders/{order_id}/tracking
```

Returns the complete immutable tracking timeline for an order.

Example lifecycle:

```text
CREATED
   ↓
ASSIGNED
   ↓
PICKED_UP
   ↓
IN_TRANSIT
   ↓
OUT_FOR_DELIVERY
   ↓
DELIVERED
```

Failed delivery example:

```text
OUT_FOR_DELIVERY
       ↓
     FAILED
       ↓
   RESCHEDULED
       ↓
    ASSIGNED
       ↓
OUT_FOR_DELIVERY
       ↓
   DELIVERED
```

### Reschedule Failed Delivery

```http
POST /api/orders/{order_id}/reschedule
```

Allows a customer to select a new delivery date and time slot after a failed delivery.

The rescheduling workflow automatically:

* Updates the order status.
* Records the event in tracking history.
* Notifies the customer.
* Recalculates agent assignment.

### Assign Delivery Agent

```http
POST /api/orders/{order_id}/assign
```

Allows an administrator to manually assign an available delivery agent.

### Trigger Auto-Assignment

```http
POST /api/orders/{order_id}/auto-assign
```

Triggers the intelligent delivery agent selection algorithm.

---

# 🚚 Delivery Agent APIs

### Get Assigned Deliveries

```http
GET /api/agents/orders
```

Returns delivery orders assigned to the authenticated agent.

### Update Availability

```http
PATCH /api/agents/availability
```

Updates whether the delivery agent is available for new assignments.

### Update Location

```http
PATCH /api/agents/location
```

Updates the delivery agent's current latitude and longitude.

The updated coordinates are used by the auto-assignment engine.

### Get Agent Profile

```http
GET /api/agents/me
```

Returns the authenticated agent's profile, availability, location, zone, and workload.

---

# 🔔 Notification System

The notification engine supports notification generation and audit logging for important order events.

Notifications can be triggered for:

* Order creation
* Agent assignment
* Delivery status changes
* Failed deliveries
* Rescheduled deliveries
* Successful delivery

Supported notification channels include:

```text
EMAIL
SMS
```

Notification records are maintained for auditing and troubleshooting.

---

# 🧮 Rate Calculation Logic

## 1. Volumetric Weight

```text
Volumetric Weight =
(L × W × H) / 5000
```

Where dimensions are measured in centimeters.

## 2. Billable Weight

```text
Billable Weight =
MAX(Actual Weight, Volumetric Weight)
```

## 3. Route Classification

```text
IF Pickup Zone == Drop Zone
    Route = INTRA-ZONE
ELSE
    Route = INTER-ZONE
```

## 4. Freight Charge

```text
Subtotal =
MAX(
    Base Rate + (Billable Weight × Per-Kg Rate),
    Minimum Charge
)
```

## 5. COD Surcharge

For COD orders:

```text
COD Fee =
Fixed Fee +
(Subtotal × Percentage / 100)
```

For prepaid orders:

```text
COD Fee = 0
```

## 6. Final Charge

```text
Total Charge =
Subtotal + COD Fee
```

---

# 🤖 Intelligent Agent Assignment

The auto-assignment engine calculates a composite score for each eligible delivery agent.

The algorithm considers:

### Geographic Distance

Haversine distance is calculated between:

```text
Agent Current Location
        ↓
Pickup Location
```

### Zone Match Bonus

Agents operating in the pickup zone receive a virtual distance reduction.

```text
Zone Match Bonus = -50 km
```

### Workload Penalty

Active deliveries increase the agent's score.

```text
Workload Penalty =
5 × Number of Active Orders
```

### Composite Score

Conceptually:

```text
Score =
Haversine Distance
+ Workload Penalty
+ Zone Adjustment
```

The agent with the **lowest score** is selected.

---

# 📊 Database Schema

The application uses relational database models for:

```text
User
Zone
AreaMapping
RateCard
CODSurcharge
AgentProfile
Order
OrderTrackingHistory
Notification
```

### Main Relationships

```text
User
 │
 ├── Customer ────────┐
 │                    │
 └── AgentProfile      │
                      ↓
                    Order
                      │
                      ↓
             OrderTrackingHistory
```

Zones are connected with area/pincode mappings and delivery agent profiles.

---

# 🧪 Testing

Run the automated integration test suite:

```bash
python test_system.py
```

The tests validate major application workflows including:

* Authentication
* Order creation
* Rate calculation
* Zone resolution
* Agent assignment
* Status transitions
* Failed delivery handling
* Rescheduling
* Tracking history
* Role-based access control

---

# 🐳 Docker

Build the Docker image:

```bash
docker build -t last-mile-delivery .
```

Run the container:

```bash
docker run -p 8000:8000 last-mile-delivery
```

Open:

```text
http://127.0.0.1:8000
```

---

# ☁️ Deployment

The project includes deployment configuration files for cloud deployment:

```text
Procfile
render.yaml
vercel.json
Dockerfile
```

For production deployment:

1. Configure environment variables.
2. Use a production database such as PostgreSQL.
3. Configure secure JWT/application secrets.
4. Configure email/SMS providers.
5. Disable demo credentials.
6. Deploy the backend using the provided deployment configuration.

---

# 🔐 Security Considerations

The platform implements role-based authorization and authenticated API access.

For production:

* Never commit `.env` files.
* Store secrets using environment variables.
* Use HTTPS.
* Replace demo passwords.
* Use a managed PostgreSQL database.
* Configure secure JWT secrets.
* Apply rate limiting to authentication endpoints.
* Validate and sanitize user input.
* Restrict administrative endpoints to authorized users.

---

# 📈 Future Enhancements

Potential improvements include:

* Real-time GPS tracking using WebSockets
* Google Maps/Mapbox route optimization
* ETA prediction using machine learning
* Delivery demand forecasting
* Dynamic pricing based on demand
* Proof-of-delivery image/signature
* OTP-based delivery verification
* Advanced analytics dashboard
* Push notifications
* Redis caching
* Background task processing with Celery
* PostgreSQL production deployment
* Kubernetes-based deployment
* CI/CD using GitHub Actions

---

# 🏗️ System Architecture

```text
                    ┌─────────────────────┐
                    │      Frontend       │
                    │ HTML/CSS/JS/Tailwind│
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │      FastAPI        │
                    │    REST API Layer   │
                    └──────────┬──────────┘
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
          ▼                    ▼                    ▼
 ┌────────────────┐   ┌────────────────┐   ┌────────────────┐
 │ Rate Engine    │   │ Assignment     │   │ Notification   │
 │                │   │ Engine         │   │ Engine         │
 └────────────────┘   └────────────────┘   └────────────────┘
          │                    │                    │
          └────────────────────┼────────────────────┘
                               ▼
                    ┌─────────────────────┐
                    │      Database       │
                    │ SQLite/PostgreSQL   │
                    └─────────────────────┘
```

---

# 📜 License

This project is developed for educational, portfolio, and demonstration purposes.

---

# 👩‍💻 Project

**Last-Mile Delivery Tracker Platform**

A full-stack logistics management system demonstrating:

* FastAPI
* Python
* SQLAlchemy
* SQLite/PostgreSQL
* JWT Authentication
* RBAC
* REST APIs
* Dynamic Pricing
* Geospatial Algorithms
* Intelligent Assignment
* Automated Testing
* Docker
* Cloud Deployment
* Responsive Frontend
