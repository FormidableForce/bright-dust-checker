"""Run the Bright Dust tracker with all-vendor sales enabled."""
import sys

import destiny_dust as tracker


def get_all_vendor_dust_sales(cfg):
    """Return non-bundle, non-decryption sales that cost Bright Dust."""
    membership_type, membership_id, character_id = tracker.find_character(cfg)
    data = tracker.api(
        cfg,
        f"/Destiny2/{membership_type}/Profile/{membership_id}/Character/{character_id}/Vendors/",
        params={"components": 402},
    )
    sales = []
    for vendor_hash, vendor in data.get("sales", {}).get("data", {}).items():
        vendor_name = tracker.name_of(cfg, "DestinyVendorDefinition", vendor_hash)
        for sale in vendor.get("saleItems", {}).values():
            cost = next(
                (
                    entry["quantity"]
                    for entry in sale.get("costs", [])
                    if entry["itemHash"] == tracker.BRIGHT_DUST
                ),
                None,
            )
            if cost is None or cost <= 0:
                continue
            definition = tracker.item_definition(cfg, sale["itemHash"])
            if tracker.is_bundle(definition):
                continue
            properties = definition.get("displayProperties", {})
            item_name = properties.get("name") or f"Unknown {sale['itemHash']}"
            if "decryption" in item_name.casefold():
                continue
            sales.append(
                {
                    "vendor": vendor_name,
                    "item": item_name,
                    "cost": cost,
                    "icon": properties.get("icon", ""),
                    "description": properties.get("description", ""),
                }
            )
    tracker.save_cache()
    tracker.save_item_cache()
    return sales


tracker.get_dust_sales = get_all_vendor_dust_sales


def list_all_vendor_sales():
    sales = tracker.get_dust_sales(tracker.load_config())
    if not sales:
        print("Nothing found for Bright Dust right now.")
        return
    current_vendor = None
    for sale in sorted(sales, key=lambda entry: (entry["vendor"], entry["item"])):
        if sale["vendor"] != current_vendor:
            current_vendor = sale["vendor"]
            print(f"\n{current_vendor}")
        print(f"  {sale['item']}: {sale['cost']} Bright Dust")


if __name__ == "__main__":
    commands = {
        "setup": tracker.setup,
        "list": list_all_vendor_sales,
        "check": tracker.cmd_check,
        "loop": tracker.cmd_loop,
        "web": tracker.cmd_web,
    }
    if len(sys.argv) < 2 or sys.argv[1] not in commands:
        sys.exit(tracker.__doc__)
    commands[sys.argv[1]]()
