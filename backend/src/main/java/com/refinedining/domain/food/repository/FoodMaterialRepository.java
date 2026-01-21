package com.refinedining.domain.food.repository;

import com.refinedining.domain.food.entity.FoodMaterial;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.Optional;

public interface FoodMaterialRepository extends JpaRepository<FoodMaterial, Long> {
    // 식품코드로 기존 데이터 존재 여부 확인
    Optional<FoodMaterial> findByFoodCd(String foodCd);
}