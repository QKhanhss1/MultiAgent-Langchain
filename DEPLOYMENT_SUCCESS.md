# Hướng dẫn build và deploy theo từng môi trường

## 1. Chuẩn bị file môi trường

- Sử dụng một trong các file sau tuỳ môi trường:
  - `.env.production` cho môi trường production
  - `.env.staging` cho môi trường staging

## 2. Build và chạy bằng Docker Compose

### Production
```sh
docker-compose --env-file .env.production up -d --build
```

### Staging
```sh
docker-compose --env-file .env.staging up -d --build
```

## 3. Kiểm tra container

- Xem logs:
  ```sh
  docker-compose logs -f ${CONTAINER_NAME}
  ```
- Kiểm tra API:
  ```sh
  curl http://localhost:${PORT}/
  ```

## 4. Lưu ý
- Thay đổi file `.env` trước khi build để đúng môi trường.
- Các biến PORT, CONTAINER_NAME sẽ được lấy tự động từ file `.env`.
- Có thể thêm biến khác vào file `.env.production` hoặc `.env.staging` nếu cần.
