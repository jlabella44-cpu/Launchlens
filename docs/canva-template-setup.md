# Canva Brand Template — Autofill Field Setup

Template ID: `EAHF7mXdlIY`
Template: "Brown and White Modern Real Estate Flyer"

## Problem

The template exists but has no autofill fields configured. The `/dataset` endpoint returns `{}`. The Canva autofill API requires data fields to be connected to design elements via Bulk Create.

## Steps

1. Open the template in the Canva editor: https://www.canva.com/brand/brand-templates/EAHF7mXdlIY

2. Open **Canva Apps** panel (left sidebar) → search for **"Bulk Create"**

3. Click **Bulk Create** → **"Enter data manually"**

4. Add these columns:

   | Column name            | Type  | Maps to                    |
   |------------------------|-------|----------------------------|
   | `property_address`     | Text  | Street address             |
   | `listing_price`        | Text  | e.g. $450,000              |
   | `bedrooms`             | Text  | Bedroom count              |
   | `bathrooms`            | Text  | Bathroom count             |
   | `square_footage`       | Text  | Sq ft                      |
   | `property_description` | Text  | Description                |
   | `agent_name`           | Text  | Agent name                 |
   | `brokerage_name`       | Text  | Brokerage                  |
   | `hero_image`           | Image | Main listing photo         |
   | `photo_2`              | Image | 2nd highest rated photo    |
   | `photo_3`              | Image | 3rd highest rated photo    |
   | `photo_4`              | Image | 4th highest rated photo    |

5. **Connect each column to a design element:**
   - Right-click a text element → "Connect data" → select the matching column
   - For images: right-click the image placeholder → "Connect data" → select the image column

6. Add a sample row of data to preview the result

7. Save (auto-saves)

## Verify

After connecting fields, run this to confirm they show up:

```bash
curl -s "https://api.canva.com/rest/v1/brand-templates/EAHF7mXdlIY/dataset" \
  -H "Authorization: Bearer $TOKEN"
```

Should return the field names. Once confirmed, tell Claude to set the template ID in production and wire it into the pipeline.

## After Fields Are Set

1. Set `CANVA_DEFAULT_TEMPLATE_ID=EAHF7mXdlIY` in production env
2. Wire `CanvaTemplateProvider` into the brand activity
3. Update `_build_autofill_data()` to include `photo_2`, `photo_3`, `photo_4`
4. Test end-to-end with a real listing
