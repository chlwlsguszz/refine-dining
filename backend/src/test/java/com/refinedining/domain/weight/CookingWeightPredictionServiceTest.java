package com.refinedining.domain.weight;

import com.refinedining.api.weight.dto.WeightPredictRequest;
import com.refinedining.api.weight.dto.WeightPredictResponse;
import com.refinedining.infra.gemini.GeminiCookingWeightClient;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.OptionalDouble;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.BDDMockito.given;

@ExtendWith(MockitoExtension.class)
class CookingWeightPredictionServiceTest {

    @Mock
    private GeminiCookingWeightClient geminiClient;

    @InjectMocks
    private CookingWeightPredictionService predictionService;

    @Test
    @DisplayName("AI 예측값과 공공데이터 단백질 농축비 기반 추정치를 함께 반환한다 (HYBRID)")
    void predictHybrid_ReturnsBothAiAndDataBasedWeight() {
        // given: 삼겹살 생것 단백질 17g/100g, 구운것 단백질 25g/100g -> 데이터 기반 수율 17/25 = 0.68 (68.0g)
        WeightPredictRequest request = new WeightPredictRequest("삼겹살", "구운것", 100.0, 17.0, 25.0);
        given(geminiClient.tryPredictWeight("삼겹살", "구운것", 100.0)).willReturn(OptionalDouble.of(70.5));

        // when
        WeightPredictResponse response = predictionService.predictHybrid(request);

        // then
        assertThat(response.getPredictedWeight()).isEqualTo(70.5);
        assertThat(response.getDataBasedWeight()).isEqualTo(68.0);
        assertThat(response.getSource()).isEqualTo("HYBRID");
        assertThat(response.getYieldRatio()).isEqualTo(0.71);
    }

    @Test
    @DisplayName("Gemini API가 비활성/실패 상태여도 공공데이터 단백질 비율이 있으면 DATA_ONLY로 정확히 추정한다")
    void predictHybrid_FallsBackToDataBasedWhenAiUnavailable() {
        // given
        WeightPredictRequest request = new WeightPredictRequest("닭가슴살", "삶은것", 200.0, 23.0, 28.75);
        given(geminiClient.tryPredictWeight("닭가슴살", "삶은것", 200.0)).willReturn(OptionalDouble.empty());

        // when
        WeightPredictResponse response = predictionService.predictHybrid(request);

        // then: 200 * (23 / 28.75) = 160.0g
        assertThat(response.getPredictedWeight()).isEqualTo(160.0);
        assertThat(response.getDataBasedWeight()).isEqualTo(160.0);
        assertThat(response.getSource()).isEqualTo("DATA_ONLY");
    }
}
