package com.refinedining.api.admin;

import com.refinedining.domain.food.raw.service.RawFoodDataService;
import com.refinedining.domain.food.refined.dto.FoodRefineReport;
import com.refinedining.domain.food.refined.service.FoodRefineService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@Slf4j
@RestController
@RequiredArgsConstructor
@RequestMapping("/api/admin/food-data")
public class AdminFoodDataController {

    private final RawFoodDataService rawFoodDataService;
    private final FoodRefineService foodRefineService;

    @Value("${admin.api-key:}")
    private String configuredAdminKey;

    @PostMapping("/sync-raw")
    public ResponseEntity<String> syncRawData(
            @RequestHeader(value = "X-Admin-Key", required = false) String requestKey) {
        validateAdminKey(requestKey);
        log.info("[ADMIN] 공공데이터 원본(Raw) 동기화 시작");
        rawFoodDataService.syncAllPublicFoodData();
        return ResponseEntity.ok("Raw 데이터 동기화 완료");
    }

    @PostMapping("/refine")
    public ResponseEntity<String> refineData(
            @RequestHeader(value = "X-Admin-Key", required = false) String requestKey) {
        validateAdminKey(requestKey);
        log.info("[ADMIN] 데이터 정제(Refine) 및 계층화 시작");
        foodRefineService.refineAll();
        return ResponseEntity.ok("데이터 정제 및 계층화 완료");
    }

    @GetMapping("/refine-report")
    public ResponseEntity<FoodRefineReport> getRefineReport(
            @RequestHeader(value = "X-Admin-Key", required = false) String requestKey) {
        validateAdminKey(requestKey);
        return ResponseEntity.ok(foodRefineService.analyzeRefinement());
    }

    private void validateAdminKey(String requestKey) {
        if (configuredAdminKey != null && !configuredAdminKey.isBlank()) {
            if (!configuredAdminKey.equals(requestKey)) {
                throw new SecurityException("유효하지 않은 관리자 API 키입니다.");
            }
        }
    }
}
