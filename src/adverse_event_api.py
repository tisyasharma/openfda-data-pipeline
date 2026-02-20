from typing import Optional

from pymongo import MongoClient

from config import MONGO_CONFIG, DB_NAME, COLLECTION_NAME


class AdverseEventAPI:
    """Abstraction layer over the OpenFDA adverse events collection in MongoDB."""

    def __init__(self, mongo_config: dict = None):
        config = mongo_config or MONGO_CONFIG
        self.client = MongoClient(**config)
        self.db = self.client[DB_NAME]
        self.collection = self.db[COLLECTION_NAME]

    def get_events_by_drug(
        self,
        drug_name: str,
        serious_only: bool = False,
        limit: int = 20,
    ) -> list[dict]:
        """Find adverse event reports where the given drug appears."""
        query = {
            "$or": [
                {"patient.drug.openfda.generic_name": {"$regex": drug_name, "$options": "i"}},
                {"patient.drug.medicinalproduct": {"$regex": drug_name, "$options": "i"}},
            ]
        }
        if serious_only:
            query["serious"] = "1"

        projection = {
            "safetyreportid": 1,
            "receivedate": 1,
            "serious": 1,
            "patient.patientsex": 1,
            "patient.patientonsetage": 1,
            "patient.reaction.reactionmeddrapt": 1,
            "_id": 0,
        }

        return list(self.collection.find(query, projection).limit(limit))

    def get_reaction_frequency(
        self,
        drug_name: str,
        top_n: int = 15,
    ) -> list[dict]:
        """Count how often each reaction appears for a given drug."""
        pipeline = [
            {"$unwind": "$patient.drug"},
            {"$match": {
                "patient.drug.openfda.generic_name": {
                    "$regex": drug_name,
                    "$options": "i",
                }
            }},
            {"$unwind": "$patient.reaction"},
            {"$group": {
                "_id": "$patient.reaction.reactionmeddrapt",
                "count": {"$sum": 1},
            }},
            {"$sort": {"count": -1}},
            {"$limit": top_n},
        ]
        return list(self.collection.aggregate(pipeline))

    def get_demographic_breakdown(
        self,
        drug_name: Optional[str] = None,
        group_by: str = "sex",
    ) -> list[dict]:
        """
        Group adverse events by a demographic dimension (sex, age, or country).
        Optionally filter to a specific drug first.
        """
        group_field_map = {
            "sex": "$patient.patientsex",
            "age": "$patient.patientonsetage",
            "country": "$primarysource.reportercountry",
        }
        group_field = group_field_map.get(group_by, "$patient.patientsex")

        pipeline = []
        if drug_name:
            pipeline.append({"$match": {
                "patient.drug.openfda.generic_name": {
                    "$regex": drug_name,
                    "$options": "i",
                }
            }})

        pipeline.extend([
            {"$group": {"_id": group_field, "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
        ])

        return list(self.collection.aggregate(pipeline))

    def get_top_drugs_by_event_count(
        self,
        serious_only: bool = False,
        top_n: int = 20,
    ) -> list[dict]:
        """Rank drugs by how many adverse event reports they appear in."""
        pipeline = []
        if serious_only:
            pipeline.append({"$match": {"serious": "1"}})

        pipeline.extend([
            {"$unwind": "$patient.drug"},
            {"$match": {"patient.drug.openfda.generic_name": {"$exists": True}}},
            {"$unwind": "$patient.drug.openfda.generic_name"},
            {"$group": {
                "_id": "$patient.drug.openfda.generic_name",
                "event_count": {"$sum": 1},
            }},
            {"$sort": {"event_count": -1}},
            {"$limit": top_n},
        ])

        return list(self.collection.aggregate(pipeline))

    def get_death_rate_by_route(
        self,
        min_reports: int = 20,
    ) -> list[dict]:
        """Compare death rates across drug administration routes."""
        pipeline = [
            {"$unwind": "$patient.drug"},
            {"$match": {"patient.drug.openfda.route": {"$exists": True}}},
            {"$unwind": "$patient.drug.openfda.route"},
            {"$group": {
                "_id": "$patient.drug.openfda.route",
                "total": {"$sum": 1},
                "deaths": {
                    "$sum": {"$cond": [{"$eq": ["$seriousnessdeath", "1"]}, 1, 0]}
                },
            }},
            {"$match": {"total": {"$gte": min_reports}}},
            {"$addFields": {
                "death_rate": {
                    "$round": [
                        {"$multiply": [{"$divide": ["$deaths", "$total"]}, 100]},
                        2,
                    ]
                }
            }},
            {"$sort": {"death_rate": -1}},
        ]
        return list(self.collection.aggregate(pipeline))

    def close(self):
        if self.client:
            self.client.close()
