package com.refinedining.domain.admin;

import com.refinedining.domain.food.service.FoodDataService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.CrossOrigin;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequiredArgsConstructor
@RequestMapping("/api/admin/food-data") // /admin 경로를 추가하여 구분
public class AdminFoodDataController {

    private final FoodDataService foodDataService;

    /**
     * [관리자 전용] 공공데이터 전체 동기화 실행
     * 인증/인가(Spring Security) 적용 시 ROLE_ADMIN 권한 필요
     */
    @PostMapping("/sync")
    public ResponseEntity<Void> syncAllData() {
        foodDataService.syncAllPublicFoodData();
        return ResponseEntity.accepted().build(); // 202 Accepted: 요청 수락됨
    }
}