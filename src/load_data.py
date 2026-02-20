import json

from pymongo import MongoClient

from config import MONGO_CONFIG, DB_NAME, COLLECTION_NAME, JSON_FILE

INDEXES = [
    "patient.drug.openfda.generic_name",
    "patient.reaction.reactionmeddrapt",
    "serious",
    "receivedate",
    "primarysource.reportercountry",
]


def load_adverse_events(filepath: str, mongo_config: dict = None) -> int:
    """Read JSON and bulk-insert into MongoDB, then build indexes."""
    config = mongo_config or MONGO_CONFIG
    client = MongoClient(**config)
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]

    # drop for idempotency
    collection.drop()

    with open(filepath, "r") as f:
        records = json.load(f)

    result = collection.insert_many(records)
    print(f"Inserted {len(result.inserted_ids)} documents into {DB_NAME}.{COLLECTION_NAME}")

    for field in INDEXES:
        collection.create_index(field)
    print(f"Created {len(INDEXES)} indexes")

    client.close()
    return len(result.inserted_ids)


def main():
    load_adverse_events(JSON_FILE)


if __name__ == "__main__":
    main()
