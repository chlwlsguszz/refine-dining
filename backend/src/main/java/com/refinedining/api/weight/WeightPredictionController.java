package com.refinedining.api.weight;

import com.refinedining.api.weight.dto.WeightPredictRequest;
import com.refinedining.api.weight.dto.WeightPredictResponse;
import com.refinedining.domain.weight.CookingWeightPredictionService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@Slf4j
@RestController
@RequiredArgsConstructor
@RequestMapping("/api/weight")
@CrossOrigin(origins = "http://localhost:5173")
public class WeightPredictionController {

    private final CookingWeightPredictionService cookingWeightPredictionService;

    @PostMapping("/predict")
    public ResponseEntity<WeightPredictResponse> predict(@Valid @RequestBody WeightPredictRequest request) {
        log.info("[AI 예측 요청] foodName={}, cookingMethod={}, baseWeight={}g",
                request.getFoodName(), request.getCookingMethod(), request.getBaseWeight());

        double predicted = cookingWeightPredictionService.predictWeightAfterCooking(
                request.getFoodName(),
                request.getCookingMethod(),
                request.getBaseWeight()
        );

        log.info("[AI 예측 완료] foodName={}, predictedWeight={}g", request.getFoodName(), predicted);
        return ResponseEntity.ok(new WeightPredictResponse(predicted));
    }
}
