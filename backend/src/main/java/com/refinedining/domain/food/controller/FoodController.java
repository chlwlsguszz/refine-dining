package com.refinedining.domain.food.controller;

import com.refinedining.domain.food.service.FoodDataService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@Slf4j
@RestController
@RequiredArgsConstructor
@RequestMapping("/api/food")
public class FoodController {

    private final FoodDataService foodDataService;

    /**
     * 공공데이터 동기화 API
     * 예시: GET http://localhost:8080/api/food/sync?page=1&size=10
     */
    @GetMapping("/sync")
    public ResponseEntity<String> syncFoodData(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size) {

        log.info("식품 데이터 동기화 요청 - page: {}, size: {}", page, size);

        try {
            foodDataService.syncFoodData(page, size);
            return ResponseEntity.ok("성공적으로 " + size + "건의 데이터를 동기화했습니다.");
        } catch (Exception e) {
            log.error("동기화 중 오류 발생: ", e);
            return ResponseEntity.internalServerError().body("동기화 실패: " + e.getMessage());
        }
    }
}