import logging
import time
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from pymongo.errors import DuplicateKeyError

from database import get_db, get_groups_col, get_tests_col, DEMO_TEST_ID, ROLE_ADMIN, ROLE_TEACHER, ROLE_STUDENT, ROLE_UNASSIGNED
from security import hash_password, verify_password, create_token, get_current_user
from models import LoginRequest, RegisterRequest, ChangeRoleRequest, ChangeGroupRequest, ChangePasswordRequest, ResetPasswordRequest, GroupBody, UpdateFullNameRequest

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/auth/setup")
async def setup_first_admin(req: LoginRequest):
    """Create the first admin user. Only works when no admin exists in the database."""
    col = get_db()
    if col.find_one({"role": ROLE_ADMIN}):
        raise HTTPException(403, "Администратор уже существует.")
    try:
        col.insert_one({
            "username": req.username,
            "password": hash_password(req.password),
            "role": ROLE_ADMIN,
            "group": "",
            "full_name": "",
            "token_version": 0,
        })
    except DuplicateKeyError:
        # User exists but is not admin — promote them
        col.update_one({"username": req.username}, {"$set": {"role": ROLE_ADMIN, "password": hash_password(req.password)}})
    logger.info("First admin '%s' created via /auth/setup", req.username)
    return {"message": f"Администратор '{req.username}' создан. Войдите в систему."}


# Simple in-memory rate limiter for login endpoint
_login_attempts: dict = defaultdict(list)
_RATE_LIMIT_WINDOW = 60  # seconds
_RATE_LIMIT_MAX = 10  # max attempts per window


@router.post("/auth/login")
async def login(req: LoginRequest):
    # Rate limiting
    now = time.time()
    _login_attempts[req.username] = [t for t in _login_attempts[req.username] if now - t < _RATE_LIMIT_WINDOW]
    if len(_login_attempts[req.username]) >= _RATE_LIMIT_MAX:
        raise HTTPException(429, "Слишком много попыток входа. Попробуйте позже.")
    _login_attempts[req.username].append(now)

    col = get_db()
    user = col.find_one({"username": req.username})
    if not user or not verify_password(req.password, user["password"]):
        raise HTTPException(401, "Неверное имя пользователя или пароль.")
    role = user.get("role", ROLE_STUDENT)
    if role == ROLE_UNASSIGNED:
        raise HTTPException(403, "Учетная запись не активирована или роль не назначена.")
    # Upgrade legacy SHA-256 hash to bcrypt on successful login
    if len(user["password"]) == 64:
        try:
            col.update_one(
                {"username": req.username},
                {"$set": {"password": hash_password(req.password)}},
            )
            logger.info("Upgraded password hash to bcrypt for user: %s", req.username)
        except Exception:
            logger.warning("Failed to upgrade password hash for user: %s", req.username)
    tv = user.get("token_version", 0)
    full_name = user.get("full_name", "")
    return {"access_token": create_token(req.username, role, tv), "role": role, "username": req.username, "full_name": full_name}


@router.post("/auth/register")
async def register(req: RegisterRequest):
    if not req.username or not req.password:
        raise HTTPException(400, "Имя пользователя и пароль не могут быть пустыми.")
    # Validate group against admin-created groups
    group = (req.group or "").strip()
    if group:
        valid_groups = [g["name"] for g in get_groups_col().find({}, {"_id": 0, "name": 1})]
        if group not in valid_groups:
            raise HTTPException(400, f"Группа '{group}' не существует. Выберите из доступных групп.")
    full_name = (req.full_name or "").strip()
    col = get_db()
    try:
        col.insert_one({
            "username": req.username,
            "password": hash_password(req.password),
            "role": ROLE_STUDENT,
            "group": group,
            "full_name": full_name,
            "token_version": 0,
        })
    except DuplicateKeyError:
        raise HTTPException(409, "Такой пользователь уже существует.")
    # Assign demo test to new user
    try:
        get_tests_col().update_one(
            {"test_id": DEMO_TEST_ID},
            {"$addToSet": {"assigned_students": req.username}},
        )
    except Exception:
        pass  # Don't fail registration if demo test assignment fails
    return {"message": "Вы успешно зарегистрировались! Можете войти в систему."}


@router.get("/auth/me")
async def get_me(user=Depends(get_current_user)):
    col = get_db()
    db_user = col.find_one({"username": user["sub"]}, {"_id": 0, "full_name": 1})
    return {"username": user["sub"], "role": user["role"], "full_name": (db_user or {}).get("full_name", "")}


@router.get("/auth/users")
async def get_all_users(user=Depends(get_current_user)):
    if user["role"] != ROLE_ADMIN:
        raise HTTPException(403, "Только для администраторов.")
    col = get_db()
    return {u["username"]: {"role": u.get("role", ROLE_UNASSIGNED), "group": u.get("group", ""), "full_name": u.get("full_name", "")} for u in col.find({}, {"_id": 0, "password": 0, "token_version": 0})}


@router.get("/auth/users/by-role/{role}")
async def get_users_by_role(role: str, user=Depends(get_current_user)):
    if user["role"] not in (ROLE_ADMIN, ROLE_TEACHER):
        raise HTTPException(403, "Недостаточно прав.")
    col = get_db()
    return [u["username"] for u in col.find({"role": role}, {"_id": 0, "username": 1})]


@router.get("/auth/groups")
async def get_groups():
    """Return list of admin-created groups (public - needed for registration)."""
    return [g["name"] for g in get_groups_col().find({}, {"_id": 0, "name": 1})]


@router.get("/auth/users/by-group/{group}")
async def get_users_by_group(group: str, user=Depends(get_current_user)):
    if user["role"] not in (ROLE_ADMIN, ROLE_TEACHER):
        raise HTTPException(403, "Недостаточно прав.")
    col = get_db()
    return [u["username"] for u in col.find({"group": group}, {"_id": 0, "username": 1})]


@router.get("/auth/students")
async def get_students(user=Depends(get_current_user)):
    """Returns all students as [{username, group}] objects."""
    if user["role"] not in (ROLE_ADMIN, ROLE_TEACHER):
        raise HTTPException(403, "Недостаточно прав.")
    col = get_db()
    return [
        {"username": u["username"], "group": u.get("group", ""), "full_name": u.get("full_name", "")}
        for u in col.find({"role": ROLE_STUDENT}, {"_id": 0, "username": 1, "group": 1, "full_name": 1})
    ]


@router.put("/auth/users/{username}/role")
async def change_role(username: str, req: ChangeRoleRequest, user=Depends(get_current_user)):
    if user["role"] != ROLE_ADMIN:
        raise HTTPException(403, "Только для администраторов.")
    if req.role not in (ROLE_ADMIN, ROLE_TEACHER, ROLE_STUDENT, ROLE_UNASSIGNED):
        raise HTTPException(400, "Недопустимая роль.")
    col = get_db()
    result = col.update_one({"username": username}, {"$set": {"role": req.role}})
    if result.matched_count == 0:
        raise HTTPException(404, "Пользователь не найден.")
    return {"message": f"Роль пользователя {username} изменена на {req.role}."}


@router.put("/auth/users/{username}/group")
async def change_group(username: str, req: ChangeGroupRequest, user=Depends(get_current_user)):
    if user["role"] != ROLE_ADMIN:
        raise HTTPException(403, "Только для администраторов.")
    group = (req.group or "").strip()
    if group and not get_groups_col().find_one({"name": group}):
        raise HTTPException(400, f"Группа '{group}' не существует.")
    col = get_db()
    result = col.update_one({"username": username}, {"$set": {"group": group}})
    if result.matched_count == 0:
        raise HTTPException(404, "Пользователь не найден.")
    logger.info("Group for user '%s' changed to '%s' by admin '%s'", username, group, user["sub"])
    display_group = group or "без группы"
    return {"message": f"Группа пользователя {username} изменена на {display_group}."}

@router.put("/auth/users/{username}/full-name")
async def update_full_name(username: str, req: UpdateFullNameRequest, user=Depends(get_current_user)):
    if user["role"] != ROLE_ADMIN:
        raise HTTPException(403, "Только для администраторов.")
    col = get_db()
    result = col.update_one({"username": username}, {"$set": {"full_name": req.full_name}})
    if result.matched_count == 0:
        raise HTTPException(404, "Пользователь не найден.")
    return {"message": f"ФИО пользователя {username} обновлено."}


@router.get("/auth/verify")
async def verify_token_endpoint(user=Depends(get_current_user)):
    col = get_db()
    db_user = col.find_one({"username": user["sub"]}, {"_id": 0, "token_version": 1, "full_name": 1})
    if db_user and db_user.get("token_version", 0) != user.get("tv", 0):
        raise HTTPException(401, "Токен недействителен. Пароль был изменён.")
    return {"username": user["sub"], "role": user["role"], "full_name": (db_user or {}).get("full_name", "")}


@router.delete("/auth/users/{username}")
async def delete_user(username: str, user=Depends(get_current_user)):
    if user["role"] != ROLE_ADMIN:
        raise HTTPException(403, "Только для администраторов.")
    col = get_db()
    target = col.find_one({"username": username})
    if not target:
        raise HTTPException(404, "Пользователь не найден.")
    if target.get("role") == ROLE_ADMIN:
        raise HTTPException(400, "Нельзя удалить администратора.")
    col.delete_one({"username": username})
    logger.info("User '%s' deleted by admin '%s'", username, user["sub"])
    return {"message": f"Пользователь {username} удалён."}


@router.put("/auth/users/{username}/password")
async def change_password(username: str, req: ChangePasswordRequest, user=Depends(get_current_user)):
    # Users can change their own password; admins can change anyone's
    if user["sub"] != username and user["role"] != ROLE_ADMIN:
        raise HTTPException(403, "Вы можете менять только свой пароль.")
    col = get_db()
    target = col.find_one({"username": username})
    if not target:
        raise HTTPException(404, "Пользователь не найден.")
    if not verify_password(req.old_password, target["password"]):
        raise HTTPException(400, "Неверный текущий пароль.")
    col.update_one({"username": username}, {
        "$set": {"password": hash_password(req.new_password)},
        "$inc": {"token_version": 1},
    })
    logger.info("Password changed for user '%s'", username)
    return {"message": "Пароль успешно изменён.", "force_logout": True}


@router.put("/auth/users/{username}/reset-password")
async def reset_password(username: str, req: ResetPasswordRequest, user=Depends(get_current_user)):
    """Admin-only: reset a user's password without requiring the old password."""
    if user["role"] != ROLE_ADMIN:
        raise HTTPException(403, "Только для администраторов.")
    col = get_db()
    target = col.find_one({"username": username})
    if not target:
        raise HTTPException(404, "Пользователь не найден.")
    col.update_one({"username": username}, {
        "$set": {"password": hash_password(req.new_password)},
        "$inc": {"token_version": 1},
    })
    logger.info("Password reset for user '%s' by admin '%s'", username, user["sub"])
    return {"message": f"Пароль пользователя {username} сброшен."}


@router.post("/auth/groups")
async def create_group(body: GroupBody, user=Depends(get_current_user)):
    """Admin-only: create a new group."""
    if user["role"] != ROLE_ADMIN:
        raise HTTPException(403, "Только для администраторов.")
    try:
        get_groups_col().insert_one({"name": body.name.strip()})
    except DuplicateKeyError:
        raise HTTPException(409, f"Группа '{body.name}' уже существует.")
    logger.info("Group '%s' created by admin '%s'", body.name, user["sub"])
    return {"message": f"Группа '{body.name}' создана."}


@router.delete("/auth/groups/{group_name}")
async def delete_group(group_name: str, user=Depends(get_current_user)):
    """Admin-only: delete a group."""
    if user["role"] != ROLE_ADMIN:
        raise HTTPException(403, "Только для администраторов.")
    result = get_groups_col().delete_one({"name": group_name})
    if result.deleted_count == 0:
        raise HTTPException(404, "Группа не найдена.")
    logger.info("Group '%s' deleted by admin '%s'", group_name, user["sub"])
    return {"message": f"Группа '{group_name}' удалена."}


@router.put("/auth/groups/{old_group_name}")
async def rename_group(old_group_name: str, body: GroupBody, user=Depends(get_current_user)):
    """Admin-only: rename a group."""
    if user["role"] != ROLE_ADMIN:
        raise HTTPException(403, "Только для администраторов.")
    new_name = body.name.strip()
    if not new_name:
        raise HTTPException(400, "Имя группы не может быть пустым.")
    if new_name == old_group_name:
        return {"message": "Название группы не изменилось."}
    # Check if new name already exists
    if get_groups_col().find_one({"name": new_name}):
        raise HTTPException(409, f"Группа '{new_name}' уже существует.")
    # Update group
    result = get_groups_col().update_one({"name": old_group_name}, {"$set": {"name": new_name}})
    if result.matched_count == 0:
        raise HTTPException(404, "Группа не найдена.")
    # Update users with this group
    get_db().update_many({"group": old_group_name}, {"$set": {"group": new_name}})
    logger.info("Group '%s' renamed to '%s' by admin '%s'", old_group_name, new_name, user["sub"])
    return {"message": f"Группа '{old_group_name}' переименована в '{new_name}'."}
