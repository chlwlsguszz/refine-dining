package com.refinedining.domain.food.raw.repository;

import com.refinedining.domain.food.raw.entity.RawFoodMaterial;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.Optional;

public interface RawFoodMaterialRepository extends JpaRepository<RawFoodMaterial, Long> {
    // 식품코드로 기존 데이터 존재 여부 확인
    Optional<RawFoodMaterial> findByFoodCd(String foodCd);
}