package com.refinedining.domain.food.refined.dto;

import java.util.List;
import java.util.Map;

public record FoodRefineReport(
        long totalRawRows,
        long retainedParents,
        long retainedChildren,
        long excludedRows,
        Map<ExclusionReason, ExclusionStats> exclusions,
        Map<String, Long> unmappedCookingCodes
) {
    public enum ExclusionReason {
        MISSING_FOOD_NAME("식품명이 null인 행"),
        SEAFOOD_NAME_FILTER("출처 코드 2 중 식품명에 대표·평균 두 단어가 모두 들어 있지 않은 행"),
        MISSING_LV6_CODE("식품 소분류 코드가 없거나 공백인 행"),
        NO_RAW_PARENT("앞선 필터를 통과한 같은 소분류에 생것(01)이 없는 행"),
        ADDITIONAL_RAW_PARENT("같은 소분류에서 첫 번째 생것 이외의 생것 행"),
        MISSING_COOKING_CODE("생것이 있는 소분류에서 세분류 코드가 없거나 공백인 행"),
        UNMAPPED_COOKING_CODE("생것이 있는 소분류에서 세분류 코드가 조리법 사전에 없는 행"),
        NO_SUPPORTED_CHILD("같은 소분류에 지원하는 조리법 자식이 없어 제외된 첫 번째 생것 행");

        private final String description;

        ExclusionReason(String description) {
            this.description = description;
        }

        public String description() {
            return description;
        }
    }

    public record ExclusionStats(String description, long count, List<RowExample> examples) {}

    public record RowExample(
            String foodCd,
            String foodNm,
            String foodLv6Cd,
            String foodLv7Cd,
            String foodLv7Nm
    ) {}
}
