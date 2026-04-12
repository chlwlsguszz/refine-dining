package com.refinedining.domain.weight;

import com.refinedining.infra.gemini.GeminiCookingWeightClient;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

@Slf4j
@Service
@RequiredArgsConstructor
public class CookingWeightPredictionService {

    private final GeminiCookingWeightClient geminiClient;

    /**
     * 조리 후 예상 중량(g)을 AI로 예측합니다.
     */
    public double predictWeightAfterCooking(String foodName, String cookingMethod, double baseWeightG) {
        return geminiClient.predictWeightAfterCooking(foodName, cookingMethod, baseWeightG);
    }
}
