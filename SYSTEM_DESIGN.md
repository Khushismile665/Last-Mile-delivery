# System Design Write-Up: Last-Mile Delivery Tracker

## 1. Rate Calculation Engine Architecture
The rate calculation engine computes accurate, dynamic delivery charges without hardcoded values. Pricing follows a multi-stage pipeline:

$$\text{Volumetric Weight (kg)} = \frac{\text{Length (cm)} \times \text{Width (cm)} \times \text{Height (cm)}}{5000}$$

$$\text{Billable Weight (kg)} = \max(\text{Actual Weight}, \text{Volumetric Weight})$$

1. **Weight Assessment**: Converts cubic dimensions to volumetric weight and bills on the higher of actual vs volumetric weight.
2. **Route Classification**: Resolves origin and destination pincodes into system zones. If Pickup Zone equals Drop Zone, the route is classified as `INTRA-ZONE`; otherwise, it is `INTER-ZONE`.
3. **Dynamic Rate Lookup**: Queries database rate cards dynamically matching the order type (`B2B` vs `B2C`) and route type (`INTRA` vs `INTER`). Freight charges are calculated as:
   $$\text{Base Freight} = \max(\text{Base Rate} + \text{Billable Weight} \times \text{Per-Kg Rate}, \text{Min Charge})$$
4. **COD Surcharge**: For Cash-on-Delivery payments, the engine applies the configured fixed fee and percentage surcharge:
   $$\text{COD Fee} = \text{Fixed Fee} + \left(\text{Base Freight} \times \frac{\text{Percentage}}{100}\right)$$
5. **Itemized Transparency**: Returns an itemized charge breakdown before order confirmation.

```
[Dimensions & Weight] ──► [Volumetric & Billable Calc] ──► [Zone & Route Detection]
                                                                  │
[Itemized Total] ◄── [COD Surcharge Applicator] ◄── [Rate Card DB Lookup]
```

## 2. Zone Detection & Area Resolution Strategy
To handle diverse addresses, the platform implements a 4-tier zone resolution algorithm:
1. **Exact Pincode Matching**: Direct lookup of origin/destination pincodes in the `area_mappings` table.
2. **Sub-string Area Matching**: Scans address text against registered area names when pincodes are missing or non-standard.
3. **Geographic Prefix Fallback**: Matches the first two digits of pincodes against regional zone codes (e.g., `11xxxx` for North Region).
4. **Default Zone Fallback**: Assigns a central hub fallback zone to prevent calculation errors.

Admin users can create new zones and dynamically assign or rebind pincodes and area names without service disruption.

## 3. Intelligent Auto-Assignment & Availability Modeling
The auto-assignment engine pairs pending orders with available delivery agents using proximity, zone alignment, and workload balancing.

```
Agent Candidates (Status == AVAILABLE)
       │
       ├── 1. Calculate Haversine Geo-Distance to Pickup Location (km)
       ├── 2. Apply Zone Match Bonus (-50km score reduction if active zone matches)
       └── 3. Apply Workload Penalty (+5 score per active assigned order)
       │
Select Lowest Composite Score Agent ──► Assign & Log Immutable Event
```

### Mathematical Scoring Function:
$$\text{Composite Score} = \text{Haversine Distance (km)} + (5.0 \times \text{Active Workload}) - (50.0 \text{ if Zone Matches else } 0.0)$$

Agents update their status (`AVAILABLE`, `ON_DELIVERY`, `OFFLINE`) and location coordinates via the agent portal. The system selects the agent with the lowest composite score, increments their workload, updates the order status to `ASSIGNED`, and sends notifications.

## 4. Failed Delivery Lifecycle & Reschedule Mechanism
Delivery failures are managed with strict validation and automated reassignment.

```
[OUT_FOR_DELIVERY] ──► Agent flags [FAILED] + Mandatory Failure Reason
                             │
                  [Customer Notified via Email/SMS]
                             │
                  Customer clicks [Reschedule] & Selects New Date
                             │
                  Status updated to [RESCHEDULED]
                             │
                  Auto-Assignment re-triggered ──► [ASSIGNED to New Agent]
```

1. **Failure Logging**: Agents must supply a mandatory failure reason (e.g., "Customer uncontactable", "Address incorrect") when updating status to `FAILED`.
2. **Customer Notification & Reschedule Window**: The customer receives an immediate notification with a link to view the failure reason and select a new target delivery date and time window.
3. **Reassignment Trigger**: Setting the status to `RESCHEDULED` automatically triggers the auto-assignment engine to select an available agent for the new date.
4. **Immutable Tracking Audit**: Every state transition logs an immutable record containing the timestamp, actor ID, actor role, location coordinates, and operational notes.
