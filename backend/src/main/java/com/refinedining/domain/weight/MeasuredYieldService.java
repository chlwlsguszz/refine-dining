package com.refinedining.domain.weight;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import jakarta.validation.constraints.*;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.List;

import com.refinedining.domain.weight.MeasuredYieldCatalog.Evidence;

@Service
public class MeasuredYieldService {
    // Earlier clients send nutrient concentrations, which do not establish a cooking yield.
    @JsonIgnoreProperties(ignoreUnknown = true)
    public record Query(@Size(max=250) String foodName, @Size(max=100) String cookingMethod,
                        @NotNull @Positive @DecimalMax("1000000") @Digits(integer=7,fraction=3) BigDecimal baseWeight,
                        @Size(max=100) String evidenceId, @Size(max=70) String foodCd) {}

    public record Prediction(String status, String explanation, BigDecimal predictedWeight,
                             BigDecimal minWeight, BigDecimal maxWeight, BigDecimal yieldPercent,
                             BigDecimal yieldRatio, String source, Evidence evidence, List<Evidence> candidates,
                             List<String> suggestedFoods) {}

    private final MeasuredYieldCatalog catalog;
    private final YieldNameSuggestions suggestions;

    public MeasuredYieldService(MeasuredYieldCatalog catalog, YieldNameSuggestions suggestions) {
        this.catalog = catalog;
        this.suggestions = suggestions;
    }

    public Prediction predict(Query input) {
        String name = MeasuredYieldCatalog.key(input.foodName()), code = MeasuredYieldCatalog.key(input.foodCd());
        if (name.isEmpty() && code.isEmpty()) throw new IllegalArgumentException("식품 이름이나 식품코드를 입력해 주세요.");
        var matches = catalog.candidates(input.foodName(), input.foodCd(), input.cookingMethod());
        if (input.evidenceId() != null && !input.evidenceId().isBlank()) {
            Evidence row = matches.stream().filter(candidate -> candidate.id().equals(input.evidenceId())).findFirst()
                    .orElseThrow(() -> new IllegalArgumentException("선택한 실측 자료가 식품 또는 조리 조건과 일치하지 않습니다."));
            return new Prediction("ESTIMATED","선택한 실험의 평균 수율로 계산했습니다.",
                    grams(input.baseWeight(),row.meanPercent()), grams(input.baseWeight(),row.minPercent()),
                    grams(input.baseWeight(),row.maxPercent()), row.meanPercent(), row.meanPercent().movePointLeft(2),
                    "MEASURED_YIELD",row,List.of(),List.of());
        }
        if (matches.isEmpty()) {
            List<String> alternatives = code.isEmpty() ? suggestions.find(input.foodName(), catalog.foodLabelsForMethod(input.cookingMethod())) : List.of();
            return unresolved("NO_MATCH","이 식품과 조리법에 맞는 실측 자료가 없습니다. 조리 후 무게를 직접 입력해 주세요.",List.of(),alternatives);
        }
        return unresolved("NEED_CONDITIONS","부위·손질 상태·조리 조건이 실제 재료와 맞는 행을 확인해 주세요.",matches,List.of());
    }

    private static Prediction unresolved(String status, String text, List<Evidence> rows, List<String> labels) {
        return new Prediction(status,text,null,null,null,null,null,null,null,rows,labels);
    }

    private static BigDecimal grams(BigDecimal raw, BigDecimal percent) {
        return percent == null ? null : raw.multiply(percent).movePointLeft(2).setScale(1, RoundingMode.HALF_UP);
    }
}
