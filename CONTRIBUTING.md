# Участие в разработке

Благодарим за интерес к платформе SLA Analytics! 

## Как внести вклад

### Сообщение об ошибках
1. Проверьте, нет ли уже открытого issue
2. Создайте новый issue через GitHub Issues
3. Используйте шаблон bug report
4. Приложите логи, шаги воспроизведения, ожидаемое и фактическое поведение

### Предложение улучшений
1. Создайте issue с меткой `enhancement`
2. Опишите проблему, которую решает предложение
3. Приложите примеры использования

### Pull Request процесс

1. Форкните репозиторий
2. Создайте ветку от `main`: `git checkout -b feature/your-feature`
3. Вносите изменения
4. Убедитесь, что код проходит проверки:
   ```bash
   # Backend
   cd backend
   pip install -r requirements.txt
   python -m pytest

   # Frontend
   cd frontend
   npm install
   npm run build
   ```
5. Сделайте коммит с понятным сообщением
6. Откройте Pull Request в `main`

### Стандарты кода

- **Python**: PEP 8, type hints, async/await для API endpoints
- **TypeScript**: strict mode, camelCase
- **Комментарии**: только когда код неочевиден
- **Тесты**: unit-тесты для новых сервисов

### Commit Convention

Используем [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add SLA breach export
fix: resolve N+1 query in dashboard overview
docs: update API documentation
refactor: extract SLA engine to separate module
test: add normalizer tests
chore: update dependencies
```

## Окружение разработки

См. `docs/development/README.md` для настройки локального окружения.
