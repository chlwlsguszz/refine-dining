package com.refinedining.api.admin;

import com.refinedining.domain.food.raw.service.RawFoodDataService;
import com.refinedining.domain.food.refined.service.FoodRefineService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@Slf4j
@RestController
@RequiredArgsConstructor
@RequestMapping("/api/admin/food-data")
public class AdminFoodDataController {

    private final RawFoodDataService rawFoodDataService;
    private final FoodRefineService foodRefineService;

    @PostMapping("/sync-raw")
    public ResponseEntity<String> syncRawData() {
        log.info("[ADMIN] 공공데이터 원본(Raw) 동기화 시작");
        rawFoodDataService.syncAllPublicFoodData();
        return ResponseEntity.ok("Raw 데이터 동기화 완료");
    }

    @PostMapping("/refine")
    public ResponseEntity<String> refineData() {
        log.info("[ADMIN] 데이터 정제(Refine) 및 도메인 생성 시작");
        foodRefineService.refineAll();
        return ResponseEntity.ok("데이터 정제 및 계층 구조 생성 완료");
    }
}