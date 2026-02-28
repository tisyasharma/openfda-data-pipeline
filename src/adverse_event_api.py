from typing import Optional

from pymongo import MongoClient

from config import MONGO_CONFIG, DB_NAME, COLLECTION_NAME


class AdverseEventAPI:
    """Query layer over the OpenFDA adverse events MongoDB collection."""

    def __init__(self, mongo_config: dict = None):
        config = mongo_config or MONGO_CONFIG
        self.client = MongoClient(**config)
        self.db = self.client[DB_NAME]
        self.collection = self.db[COLLECTION_NAME]

    def get_events_by_drug(self, drug_name: str, serious_only: bool = False, limit: int = 20,) -> list[dict]:
        """
        Returns adverse event reports for a given drug. We search both
        openfda.generic_name and medicinalproduct since not all records have
        the openfda fields filled in. Use serious_only=True to only get reports
        flagged as serious.

        Args:
            drug_name: partial or full drug name to search for (case-insensitive)
            serious_only: if True, only returns reports marked as serious
            limit: maximum number of reports to return
        """
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

    def get_reaction_frequency(self, drug_name: str, top_n: int = 15,) -> list[dict]:
        """
        Returns the most commonly reported reactions for a given drug, sorted by
        how often they appear. Each report can have multiple drugs and reactions
        stored as arrays, so we unwind both to count each reaction on its own.

        Args:
            drug_name: drug name to filter by (case-insensitive match on openfda.generic_name)
            top_n: number of reactions to return, sorted by descending frequency
        """
        pipeline = [
            # each report has an array of drugs, unwind to filter by name
            {"$unwind": "$patient.drug"},
            {"$match": {
                "patient.drug.openfda.generic_name": {
                    "$regex": drug_name,
                    "$options": "i",
                }
            }},
            # each patient can have multiple reactions, unwind so we count each one
            {"$unwind": "$patient.reaction"},
            {"$group": {
                "_id": "$patient.reaction.reactionmeddrapt",
                "count": {"$sum": 1},
            }},
            {"$sort": {"count": -1}},
            {"$limit": top_n},
        ]
        return list(self.collection.aggregate(pipeline))

    def get_demographic_breakdown(self, drug_name: Optional[str] = None, group_by: str = "sex",) -> list[dict]:
        """
        Groups report counts by sex, age, or country. If a drug name is given,
        we filter to just that drug's reports before grouping.

        Args:
            drug_name: optional drug name to filter by before grouping
            group_by: field to group on — one of "sex", "age", or "country" (defaults to "sex")
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

    def get_top_drugs_by_event_count(self, serious_only: bool = False, top_n: int = 20,) -> list[dict]:
        """
        Returns the drugs that appear in the most adverse event reports. NOTE: We group
        by openfda.generic_name instead of medicinalproduct since the latter is
        too inconsistently formatted to rely on.

        Args:
            serious_only: if True, only counts reports marked as serious
            top_n: how many drugs to return, sorted by report count
        """
        pipeline = []
        if serious_only:
            pipeline.append({"$match": {"serious": "1"}})

        pipeline.extend([
            {"$unwind": "$patient.drug"},
            {"$match": {"patient.drug.openfda.generic_name": {"$exists": True}}},
            # generic_name is an array field, unwind so we can group by individual values
            {"$unwind": "$patient.drug.openfda.generic_name"},
            {"$group": {
                "_id": "$patient.drug.openfda.generic_name",
                "event_count": {"$sum": 1},
            }},
            {"$sort": {"event_count": -1}},
            {"$limit": top_n},
        ])

        return list(self.collection.aggregate(pipeline))

    def get_death_rate_by_route(self, min_reports: int = 20,) -> list[dict]:
        """
        Calculates the percentage of reports that included a death outcome, broken
        down by administration route. Routes with very few reports are filtered out
        using min_reports to avoid misleading statistics from small samples.

        Args:
            min_reports: minimum number of reports a route needs to be included in results
        """
        pipeline = [
            {"$unwind": "$patient.drug"},
            {"$match": {"patient.drug.openfda.route": {"$exists": True}}},
            # route is an array field, unwind so we can group by each individual route
            {"$unwind": "$patient.drug.openfda.route"},
            {"$group": {
                "_id": "$patient.drug.openfda.route",
                "total": {"$sum": 1},
                # count 1 if the report includes a death, 0 otherwise
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
