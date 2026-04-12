
```
refine-dining
├─ backend
│  ├─ build.gradle
│  ├─ db_food_lv7_analysis.csv
│  ├─ gradle
│  │  └─ wrapper
│  │     ├─ gradle-wrapper.jar
│  │     └─ gradle-wrapper.properties
│  ├─ gradlew
│  ├─ gradlew.bat
│  ├─ HELP.md
│  ├─ settings.gradle
│  └─ src
│     ├─ main
│     │  ├─ java
│     │  │  └─ com
│     │  │     └─ refinedining
│     │  │        ├─ api
│     │  │        │  ├─ admin
│     │  │        │  │  └─ AdminFoodDataController.java
│     │  │        │  └─ food
│     │  │        │     └─ FoodController.java
│     │  │        ├─ BackendApplication.java
│     │  │        ├─ domain
│     │  │        │  └─ food
│     │  │        │     ├─ raw
│     │  │        │     │  ├─ entity
│     │  │        │     │  │  └─ RawFoodMaterial.java
│     │  │        │     │  ├─ repository
│     │  │        │     │  │  └─ RawFoodMaterialRepository.java
│     │  │        │     │  └─ service
│     │  │        │     │     └─ RawFoodDataService.java
│     │  │        │     └─ refined
│     │  │        │        ├─ dto
│     │  │        │        │  ├─ FoodChildResponse.java
│     │  │        │        │  └─ FoodSearchResponse.java
│     │  │        │        ├─ entity
│     │  │        │        │  ├─ CookingMethod.java
│     │  │        │        │  └─ FoodMaterial.java
│     │  │        │        ├─ repository
│     │  │        │        │  └─ FoodMaterialRepository.java
│     │  │        │        └─ service
│     │  │        │           ├─ FoodRefineService.java
│     │  │        │           └─ FoodSearchService.java
│     │  │        ├─ global
│     │  │        │  └─ config
│     │  │        │     └─ RestTemplateConfig.java
│     │  │        └─ infra
│     │  │           └─ publicdata
│     │  │              ├─ dto
│     │  │              │  └─ PublicNutriResponse.java
│     │  │              └─ PublicDataClient.java
│     │  └─ resources
│     │     ├─ application-local.yml
│     │     ├─ application.yml
│     │     ├─ static
│     │     └─ templates
│     └─ test
│        ├─ java
│        │  └─ com
│        │     └─ refinedining
│        │        ├─ BackendApplicationTests.java
│        │        ├─ ConfigLoadDebugTest.java
│        │        ├─ domain
│        │        │  └─ food
│        │        │     ├─ analysis
│        │        │     │  └─ RawFoodDataDbAnalysisTest.java
│        │        │     └─ service
│        │        │        └─ RawFoodDataServiceTest.java
│        │        └─ infra
│        │           └─ publicdata
│        │              └─ PublicApiConnectionTest.java
│        └─ resources
│           └─ application-test.yml
└─ frontend
   ├─ eslint.config.js
   ├─ index.html
   ├─ package-lock.json
   ├─ package.json
   ├─ public
   │  └─ vite.svg
   ├─ README.md
   ├─ src
   │  ├─ App.css
   │  ├─ App.jsx
   │  ├─ assets
   │  │  └─ react.svg
   │  ├─ index.css
   │  ├─ main.jsx
   │  ├─ pages
   │  │  ├─ ComparePage.jsx
   │  │  └─ SearchPage.jsx
   │  └─ styles
   │     ├─ commonStyles.js
   │     └─ theme.jsx
   └─ vite.config.js

```