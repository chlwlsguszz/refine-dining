package com.refinedining.domain.food.refined.repository;

import com.refinedining.domain.food.refined.entity.FoodMaterial;
import org.springframework.data.jpa.repository.JpaRepository;

public interface FoodMaterialRepository extends JpaRepository<FoodMaterial, Long> {
}
