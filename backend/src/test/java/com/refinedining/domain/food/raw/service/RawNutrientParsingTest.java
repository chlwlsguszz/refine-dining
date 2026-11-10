package com.refinedining.domain.food.raw.service;

import static org.assertj.core.api.Assertions.assertThat;
import org.junit.jupiter.api.Test;

class RawNutrientParsingTest {
    @Test
    void retainsMeasuredZeroAndMissingValues() {
        assertThat(RawFoodDataService.parseDouble("0.00")).isZero();
        assertThat(RawFoodDataService.parseDouble("0.10")).isEqualTo(.10);
        for (String absent : new String[]{null, "", "-", "N/A", "NaN", "Infinity", "?"}) {
            assertThat(RawFoodDataService.parseDouble(absent)).isNull();
        }
    }
}
