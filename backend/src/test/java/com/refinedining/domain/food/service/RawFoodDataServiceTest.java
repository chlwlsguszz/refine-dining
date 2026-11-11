package com.refinedining.domain.food.service;

import com.refinedining.domain.food.raw.entity.RawFoodMaterial;
import com.refinedining.domain.food.raw.repository.RawFoodMaterialRepository;
import com.refinedining.domain.food.raw.service.RawFoodDataService;
import com.refinedining.infra.publicdata.PublicDataClient;
import com.refinedining.infra.publicdata.dto.PublicNutriResponse;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.Collections;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.anyCollection;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.BDDMockito.given;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;

@ExtendWith(MockitoExtension.class)
class RawFoodDataServiceTest {

    @Mock
    private PublicDataClient publicDataClient;

    @Mock
    private RawFoodMaterialRepository rawFoodMaterialRepository;

    @InjectMocks
    private RawFoodDataService foodDataService;

    @Test
    @DisplayName("공공데이터 API로부터 받은 데이터를 일괄 조회 후 신규 데이터를 DB에 저장한다.")
    @SuppressWarnings("unchecked")
    void syncPublicFoodData_Success() {
        // given
        PublicNutriResponse.NutriItem mockItem = new PublicNutriResponse.NutriItem(
                "D000001", "고등어, 생것", "D", "원재료", "1", "수산물",
                "01", "어류", "0101", "고등어", "010101", "고등어류", "01010101", "고등어", "01", "생것",
                "100g", "183", "65.0", "20.2", "10.5", "1.2", "0", "-", "N/A",
                "24", "1.2", "210", "320", "110", "15", "15", "0", "0.1", "0.3", "8.5", "1.0", "5.0", "60", "2.5", "0",
                "30", "1", "식약처", "KR", "국산", "-", "N", "1", "분석", "20240101", "-", "20240101", "I001", "식품의약품안전처"
        );

        PublicNutriResponse mockResponse = new PublicNutriResponse(
                new PublicNutriResponse.Response(
                        new PublicNutriResponse.Header("00", "NORMAL_CODE"),
                        new PublicNutriResponse.Body(List.of(mockItem), 1)
                )
        );

        given(publicDataClient.fetchNutriData(anyInt(), anyInt())).willReturn(mockResponse);
        given(rawFoodMaterialRepository.findAllByFoodCdIn(anyCollection())).willReturn(Collections.emptyList());

        // when
        foodDataService.syncPublicFoodData(1, 10);

        // then
        ArgumentCaptor<List<RawFoodMaterial>> captor = ArgumentCaptor.forClass(List.class);
        verify(rawFoodMaterialRepository, times(1)).saveAll(captor.capture());

        List<RawFoodMaterial> saved = captor.getValue();
        assertThat(saved).hasSize(1);
        assertThat(saved.get(0).getFoodCd()).isEqualTo("D000001");
        assertThat(saved.get(0).getEnerc()).isEqualTo(183.0);
        assertThat(saved.get(0).getProt()).isEqualTo(20.2);
        // "-" 및 "N/A" 특수문자 파싱 검증
        assertThat(saved.get(0).getSugar()).isNull();
        assertThat(saved.get(0).getFibtg()).isNull();
        assertThat(saved.get(0).getChocdf()).isEqualTo(0.0);
    }
}
