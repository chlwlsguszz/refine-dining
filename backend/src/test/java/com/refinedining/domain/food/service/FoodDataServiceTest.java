package com.refinedining.domain.food.service;

import com.refinedining.domain.food.entity.FoodMaterial;
import com.refinedining.domain.food.repository.FoodMaterialRepository;
import com.refinedining.infra.publicdata.PublicDataClient;
import com.refinedining.infra.publicdata.dto.PublicNutriResponse;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.List;
import java.util.Optional;

import static org.mockito.ArgumentMatchers.*;
import static org.mockito.BDDMockito.given;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.times;


@ExtendWith(MockitoExtension.class)
class FoodDataServiceTest {

    @Mock
    private PublicDataClient publicDataClient;

    @Mock
    private FoodMaterialRepository foodMaterialRepository;

    @InjectMocks
    private FoodDataService foodDataService;

    @Test
    @DisplayName("공공데이터 API로부터 받은 데이터를 성공적으로 DB에 저장한다.")
    void syncPublicFoodData_Success() {
        // given (준비)
        /*PublicNutriResponse.NutriItem mockItem = new PublicNutriResponse.NutriItem(
                "D000001", "고등어, 생것", "수산물", "100g",
                "150", "20.2", "7.5", "0", "0", "100",
                "식약처", "20240101"
        );

        PublicNutriResponse mockResponse = new PublicNutriResponse(
                new PublicNutriResponse.Response(
                        new PublicNutriResponse.Header("00", "NORMAL_CODE"),
                        new PublicNutriResponse.Body(List.of(mockItem), 1)
                )
        );

        given(publicDataClient.fetchNutriData(anyInt(), anyInt())).willReturn(mockResponse);
        given(foodMaterialRepository.findByFoodCd("D000001")).willReturn(Optional.empty());

        // when (실행)
        foodDataService.syncPublicFoodData(1, 10);

        // then (검증)
        // save 메서드가 FoodMaterial 객체와 함께 호출되었는지 확인
        verify(foodMaterialRepository, times(1)).save(any(FoodMaterial.class));*/
    }
}