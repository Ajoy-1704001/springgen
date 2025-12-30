# 🌱 SpringGen

**SpringGen** is an interactive CLI tool that generates ready-to-run **Spring Boot CRUD boilerplate code** — complete with Entities, Repositories, Services, and Controllers — using configurable templates.

---

## 🚀 Features

✅ Interactive CLI (no arguments needed)  
✅ Supports **pagination** and **sorting** (configurable defaults)  
✅ Uses **YAML config** stored under `~/.springgen/config.yml`  
✅ Generates clean, **Lombok-based** classes with constructor injection  
✅ **Jinja2-powered templates** (easy to customize)  
✅ Auto-detects `jakarta.persistence` or `javax.persistence`
✅ Configurable primary key type & generation strategy (global + per entity) ⭐
✅ Single-folder package mode for compact architectures
✅ Live config editing via CLI or editor
✅ Works cross-platform (Linux / macOS / Windows)

---

## 🧩 Installation

```bash
pip install springgen
```

Requires Python ≥ 3.8

⚙️ Usage
Simply run:

```bash
springgen
```
You’ll be prompted for entity names and which layers to generate:

```pgsql
Enter entity names (comma-separated): Product, Category
Do you want to generate Repository layer for all entities? [y/n]: y
Do you want to generate Service layer (interface + impl) for all entities? [y/n]: y
Do you want to generate Controller layer for all entities? [y/n]: y
```

SpringGen will generate:

```swift
src/main/java/com/example/demo/
 ├─ model/
 │   └─ Product.java
 ├─ repository/
 │   └─ ProductRepository.java
 ├─ service/
 │   ├─ ProductService.java
 │   └─ impl/ProductServiceImpl.java
 └─ controller/
     └─ ProductController.java
```

⚙️ Configuration
SpringGen stores configuration at:

```arduino
~/.springgen/config.yml
```

🧾 Default Config

```yaml
base_package: com.example.demo
persistence_package: auto    # auto | jakarta.persistence | javax.persistence
features:
  pagination_and_sorting: true
api:
  defaultPageSize: 10
  defaultSort: id,asc
folders:
  entity: model
  repository: repository
  service: service
  controller: controller
entity:
  primary_key:
    name: id
    type: Long
    strategy: IDENTITY
```
Edit interactively

```bash
springgen --config
```
Open in your editor

```bash
springgen --edit-config
```

Change settings via CLI

```bash
springgen --set api.defaultPageSize=25
springgen --set features.pagination_and_sorting=false
```

🧠 Example Generated Code
✅ Entity
```java
@Entity
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Product {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
}```

✅ Repository
```java
@Repository
public interface ProductRepository extends JpaRepository<Product, Long> {}
```

✅ Service (with pagination)
```java
public interface ProductService {
    Product getById(Long id);
    Product save(Product obj);
    Product update(Product obj);
    Page<Product> getPage(Pageable pageable);
    void delete(Long id);
}```

✅ Controller
```java
@RestController
@RequestMapping("/products")
@RequiredArgsConstructor
public class ProductController {

    private final ProductService service;

    @GetMapping
    public ResponseEntity<?> getAll(
        @PageableDefault(page = 0, size = 10, sort = "id", direction = Sort.Direction.ASC)
        Pageable pageable) {
        Page<Product> page = service.getPage(pageable);
        return ResponseEntity.ok(page);
    }

    // other CRUD methods...
}
```
🧰 Advanced
📦 Single-folder mode
Put everything inside one package:

```bash
springgen --single-folder common
```

🧩 Developer Info

👨‍💻 Author

Ajoy Deb Nath

🔗 GitHub: [Ajoy-1704001](https://github.com/Ajoy-1704001)