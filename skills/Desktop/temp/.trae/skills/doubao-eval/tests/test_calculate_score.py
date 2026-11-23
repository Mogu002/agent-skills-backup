from __future__ import annotations

import unittest

from scripts.calculate_score import ScoreError, score_item, score_payload


class CalculateScoreTests(unittest.TestCase):
    @staticmethod
    def configuration(**overrides: int | str) -> dict[str, int | str]:
        values: dict[str, int | str] = {
            "workflow": "NA",
            "dashboard": "NA",
            "permission": "NA",
            "form": "NA",
            "table": "NA",
        }
        values.update(overrides)
        return values

    def test_reference_na_example(self) -> None:
        result = score_item(
            {
                "task_type": "create",
                "dimensions": {
                    "table_design": 0,
                    "data_reasonableness": "/",
                    "configuration_correctness": self.configuration(form=1),
                    "artifact_richness": 0,
                },
            }
        )
        self.assertEqual(result["score"], "0.4375")
        self.assertEqual(result["display_score"], "0.44")
        self.assertEqual(
            result["human_eval_fields"]["产物丰富度【创建类题目专有】"],
            "有问题",
        )

    def test_child_zero_collapses_dimension(self) -> None:
        result = score_item(
            {
                "task_type": "create",
                "dimensions": {
                    "table_design": 1,
                    "data_reasonableness": 1,
                    "configuration_correctness": self.configuration(
                        workflow=1, dashboard=0
                    ),
                    "artifact_richness": 1,
                },
            }
        )
        self.assertEqual(result["resolved_dimensions"]["configuration_correctness"], 0)
        self.assertEqual(result["score"], "0.65")

    def test_edit_reweights_na_dimension(self) -> None:
        result = score_item(
            {
                "task_type": "编辑类",
                "dimensions": {
                    "table_design": 0,
                    "data_reasonableness": "NA",
                    "configuration_correctness": self.configuration(form=1),
                },
            }
        )
        self.assertEqual(result["score"], "0.5")

    def test_data_analysis(self) -> None:
        result = score_item(
            {"task_type": "数据分析", "dimensions": {"instruction_following": 1}}
        )
        self.assertEqual(result["score"], "1")

    def test_reference_batch_macro_average(self) -> None:
        payload = {
            "items": [
                {
                    "id": "1",
                    "task_type": "create",
                    "dimensions": {
                        "table_design": 0,
                        "data_reasonableness": 0,
                        "configuration_correctness": self.configuration(form=1),
                        "artifact_richness": 0,
                    },
                },
                {
                    "id": "2",
                    "task_type": "create",
                    "dimensions": {
                        "table_design": 0,
                        "data_reasonableness": 0,
                        "configuration_correctness": self.configuration(form=1),
                        "artifact_richness": 0,
                    },
                },
                {
                    "id": "3",
                    "task_type": "create",
                    "dimensions": {
                        "table_design": 1,
                        "data_reasonableness": 1,
                        "configuration_correctness": self.configuration(form=1),
                        "artifact_richness": 0,
                    },
                },
                {
                    "id": "4",
                    "task_type": "create",
                    "dimensions": {
                        "table_design": 0,
                        "data_reasonableness": "/",
                        "configuration_correctness": self.configuration(form=1),
                        "artifact_richness": 0,
                    },
                },
            ]
        }
        aggregate = score_payload(payload)["aggregate"]
        self.assertEqual(aggregate["score"], "0.509375")
        self.assertEqual(aggregate["rounded_integer_percent"], 51)

    def test_rejects_bool(self) -> None:
        with self.assertRaises(ScoreError) as caught:
            score_item(
                {
                    "task_type": "data_analysis",
                    "dimensions": {"instruction_following": True},
                }
            )
        self.assertEqual(caught.exception.code, "E_INVALID_RATING")

    def test_rejects_missing_dimension(self) -> None:
        with self.assertRaises(ScoreError) as caught:
            score_item(
                {
                    "task_type": "edit",
                    "dimensions": {
                        "table_design": 1,
                        "configuration_correctness": 1,
                    },
                }
            )
        self.assertEqual(caught.exception.code, "E_MISSING_DIMENSION")

    def test_rejects_all_na(self) -> None:
        with self.assertRaises(ScoreError) as caught:
            score_item(
                {
                    "task_type": "edit",
                    "dimensions": {
                        "table_design": "NA",
                        "data_reasonableness": "NA",
                        "configuration_correctness": self.configuration(),
                    },
                }
            )
        self.assertEqual(caught.exception.code, "E_NO_APPLICABLE_DIMENSIONS")

    def test_human_eval_fields_match_form_example(self) -> None:
        result = score_item(
            {
                "id": "37",
                "task_type": "编辑类",
                "dimensions": {
                    "table_design": "NA",
                    "data_reasonableness": "NA",
                    "configuration_correctness": self.configuration(form=1),
                },
            }
        )
        self.assertEqual(
            result["human_eval_fields"],
            {
                "数据表设计": "不涉及",
                "数据合理性": "不涉及",
                "Workflow配置": "不涉及",
                "Dashboard 配置": "不涉及",
                "Permission配置": "不涉及",
                "Form 配置正确": "无问题",
                "Table 配置正确": "不涉及",
                "指令遵从【数据分析专有】": "不涉及",
                "产物丰富度【创建类题目专有】": "不涉及",
                "最终分数": "1",
            },
        )
        self.assertEqual(
            list(result["human_eval_fields"]),
            [
                "数据表设计",
                "数据合理性",
                "Workflow配置",
                "Dashboard 配置",
                "Permission配置",
                "Form 配置正确",
                "Table 配置正确",
                "指令遵从【数据分析专有】",
                "产物丰富度【创建类题目专有】",
                "最终分数",
            ],
        )

    def test_data_analysis_human_eval_fields(self) -> None:
        result = score_item(
            {"task_type": "data_analysis", "dimensions": {"instruction_following": 0}}
        )
        self.assertEqual(result["human_eval_fields"]["指令遵从【数据分析专有】"], "有问题")
        self.assertEqual(result["human_eval_fields"]["Form 配置正确"], "不涉及")
        self.assertEqual(result["human_eval_fields"]["最终分数"], "0")

    def test_create_table_only_query_scoped_richness(self) -> None:
        result = score_item(
            {
                "task_type": "create",
                "dimensions": {
                    "table_design": 1,
                    "data_reasonableness": "NA",
                    "configuration_correctness": self.configuration(),
                    "artifact_richness": "NA_QUERY",
                },
            }
        )
        self.assertEqual(result["resolved_dimensions"]["artifact_richness"], "NA_QUERY")
        self.assertEqual(
            result["human_eval_fields"]["产物丰富度【创建类题目专有】"],
            "不涉及（query要求）",
        )
        self.assertEqual(result["applicable_weight_sum"], "0.35")
        self.assertEqual(result["score"], "1")

    def test_create_explicit_multiple_types_accepts_chinese_alias(self) -> None:
        result = score_item(
            {
                "task_type": "创建类",
                "dimensions": {
                    "table_design": 1,
                    "data_reasonableness": "NA",
                    "configuration_correctness": self.configuration(form=1),
                    "artifact_richness": "不涉及（query要求）",
                },
            }
        )
        self.assertEqual(result["resolved_dimensions"]["artifact_richness"], "NA_QUERY")
        self.assertEqual(
            result["human_eval_fields"]["产物丰富度【创建类题目专有】"],
            "不涉及（query要求）",
        )
        self.assertEqual(result["applicable_weight_sum"], "0.7")
        self.assertEqual(result["score"], "1")

    def test_query_scoped_richness_reweights_create_denominator(self) -> None:
        result = score_item(
            {
                "task_type": "create",
                "dimensions": {
                    "table_design": 1,
                    "data_reasonableness": 0,
                    "configuration_correctness": self.configuration(form=1),
                    "artifact_richness": "NA_QUERY",
                },
            }
        )
        self.assertEqual(result["applicable_weight_sum"], "0.9")
        self.assertEqual(result["display_score"], "0.78")

    def test_query_scoped_na_is_rejected_outside_create_richness(self) -> None:
        with self.assertRaises(ScoreError) as caught:
            score_item(
                {
                    "task_type": "create",
                    "dimensions": {
                        "table_design": "NA_QUERY",
                        "data_reasonableness": 1,
                        "configuration_correctness": self.configuration(form=1),
                        "artifact_richness": 1,
                    },
                }
            )
        self.assertEqual(caught.exception.code, "E_QUERY_SCOPED_NA_NOT_ALLOWED")

    def test_requires_all_configuration_subdomains(self) -> None:
        with self.assertRaises(ScoreError) as caught:
            score_item(
                {
                    "task_type": "edit",
                    "dimensions": {
                        "table_design": 1,
                        "data_reasonableness": 1,
                        "configuration_correctness": {"form": 1},
                    },
                }
            )
        self.assertEqual(caught.exception.code, "E_MISSING_CONFIGURATION_SUBDOMAIN")

    def test_rejects_scalar_configuration_rating(self) -> None:
        with self.assertRaises(ScoreError) as caught:
            score_item(
                {
                    "task_type": "edit",
                    "dimensions": {
                        "table_design": 1,
                        "data_reasonableness": 1,
                        "configuration_correctness": 1,
                    },
                }
            )
        self.assertEqual(caught.exception.code, "E_CONFIGURATION_SUBDOMAINS_REQUIRED")

    def test_rejects_unknown_configuration_subdomain(self) -> None:
        configuration = self.configuration(form=1)
        configuration["chart"] = 1
        with self.assertRaises(ScoreError) as caught:
            score_item(
                {
                    "task_type": "create",
                    "dimensions": {
                        "table_design": 1,
                        "data_reasonableness": 1,
                        "configuration_correctness": configuration,
                        "artifact_richness": 1,
                    },
                }
            )
        self.assertEqual(caught.exception.code, "E_UNKNOWN_CONFIGURATION_SUBDOMAIN")


if __name__ == "__main__":
    unittest.main()
