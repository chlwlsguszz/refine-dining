package com.refinedining.domain.food.refined.service;

import com.refinedining.domain.food.raw.entity.RawFoodMaterial;
import com.refinedining.domain.food.refined.dto.FoodRefineReport;
import com.refinedining.domain.food.refined.dto.FoodRefineReport.ExclusionReason;
import com.refinedining.domain.food.refined.dto.FoodRefineReport.ExclusionStats;
import com.refinedining.domain.food.refined.dto.FoodRefineReport.RowExample;
import com.refinedining.domain.food.refined.entity.CookingMethod;

import java.util.ArrayList;
import java.util.Collections;
import java.util.EnumMap;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

final class FoodRefinementPlan {

    private static final int MAX_EXAMPLES_PER_REASON = 3;

    record RetainedGroup(RawFoodMaterial parent, List<RawFoodMaterial> children) {}

    private final int totalRawRows;
    private final List<RetainedGroup> retainedGroups = new ArrayList<>();
    private final Map<ExclusionReason, ReasonTally> exclusions = new EnumMap<>(ExclusionReason.class);
    private final Map<String, Long> unmappedCookingCodes = new TreeMap<>();

    private FoodRefinementPlan(int totalRawRows) {
        this.totalRawRows = totalRawRows;
        for (ExclusionReason reason : ExclusionReason.values()) {
            exclusions.put(reason, new ReasonTally());
        }
    }

    static FoodRefinementPlan from(List<RawFoodMaterial> rawRows) {
        FoodRefinementPlan plan = new FoodRefinementPlan(rawRows.size());
        Map<String, List<RawFoodMaterial>> groups = new HashMap<>();
        for (RawFoodMaterial row : rawRows) {
            ExclusionReason reason = initialExclusion(row);
            if (reason == null) {
                groups.computeIfAbsent(row.getFoodLv6Cd(), key -> new ArrayList<>()).add(row);
            } else {
                plan.exclude(row, reason);
            }
        }
        groups.values().forEach(plan::classifyGroup);
        return plan;
    }

    private static ExclusionReason initialExclusion(RawFoodMaterial row) {
        String name = row.getFoodNm();
        if (name == null) {
            return ExclusionReason.MISSING_FOOD_NAME;
        }
        if ("2".equals(row.getSrcCd()) && !(name.contains("대표") && name.contains("평균"))) {
            return ExclusionReason.SEAFOOD_NAME_FILTER;
        }
        if (row.getFoodLv6Cd() == null || row.getFoodLv6Cd().isBlank()) {
            return ExclusionReason.MISSING_LV6_CODE;
        }
        return null;
    }

    private void classifyGroup(List<RawFoodMaterial> rows) {
        RawFoodMaterial parent = rows.stream()
                .filter(row -> CookingMethod.RAW.getCode().equals(row.getFoodLv7Cd()))
                .findFirst()
                .orElse(null);
        if (parent == null) {
            rows.forEach(row -> exclude(row, ExclusionReason.NO_RAW_PARENT));
            return;
        }

        List<RawFoodMaterial> children = new ArrayList<>();
        for (RawFoodMaterial row : rows) {
            if (row == parent) {
                continue;
            }
            ExclusionReason reason = childExclusion(row.getFoodLv7Cd());
            if (reason == null) {
                children.add(row);
            } else {
                exclude(row, reason);
            }
        }
        if (children.isEmpty()) {
            exclude(parent, ExclusionReason.NO_SUPPORTED_CHILD);
        } else {
            retainedGroups.add(new RetainedGroup(parent, List.copyOf(children)));
        }
    }

    private static ExclusionReason childExclusion(String cookingCode) {
        if (CookingMethod.RAW.getCode().equals(cookingCode)) {
            return ExclusionReason.ADDITIONAL_RAW_PARENT;
        }
        if (cookingCode == null || cookingCode.isBlank()) {
            return ExclusionReason.MISSING_COOKING_CODE;
        }
        if (CookingMethod.findByCode(cookingCode) == null) {
            return ExclusionReason.UNMAPPED_COOKING_CODE;
        }
        return null;
    }

    private void exclude(RawFoodMaterial row, ExclusionReason reason) {
        exclusions.get(reason).record(row);
        if (reason == ExclusionReason.UNMAPPED_COOKING_CODE) {
            unmappedCookingCodes.merge(row.getFoodLv7Cd(), 1L, Long::sum);
        }
    }

    List<RetainedGroup> retainedGroups() {
        return Collections.unmodifiableList(retainedGroups);
    }

    FoodRefineReport report() {
        Map<ExclusionReason, ExclusionStats> stats = new EnumMap<>(ExclusionReason.class);
        exclusions.forEach((reason, tally) -> stats.put(reason,
                new ExclusionStats(reason.description(), tally.count, List.copyOf(tally.examples))));
        long excludedRows = exclusions.values().stream().mapToLong(tally -> tally.count).sum();
        long retainedChildren = retainedGroups.stream().mapToLong(group -> group.children().size()).sum();
        return new FoodRefineReport(totalRawRows, retainedGroups.size(), retainedChildren, excludedRows,
                Collections.unmodifiableMap(stats), Collections.unmodifiableMap(unmappedCookingCodes));
    }

    private static final class ReasonTally {
        private long count;
        private final List<RowExample> examples = new ArrayList<>();

        private void record(RawFoodMaterial row) {
            count++;
            if (examples.size() < MAX_EXAMPLES_PER_REASON) {
                examples.add(new RowExample(row.getFoodCd(), row.getFoodNm(), row.getFoodLv6Cd(),
                        row.getFoodLv7Cd(), row.getFoodLv7Nm()));
            }
        }
    }
}
