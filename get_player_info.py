from sessions import session, neighbor_session, neighbors
from engine import timestamp_now

def get_player_info(USERID):
    # Update last logged in
    ts_now = timestamp_now()
    session(USERID)["playerInfo"]["last_logged_in"] = ts_now
    # player
    player_info = {
        "result": "ok",
        "processed_errors": 0,
        "timestamp": ts_now,
        "playerInfo": session(USERID)["playerInfo"],
        "map": session(USERID)["maps"][0],
        "privateState": session(USERID)["privateState"],
        "neighbors": neighbors(USERID)
    }
    return player_info

def get_neighbor_info(userid, map_number):
    komsu = neighbor_session(userid)
    if komsu is None:
        # Silinmiş/bilinmeyen komşu: sunucu 500 vermesin.
        return {"result": "error", "processed_errors": 0, "timestamp": timestamp_now()}
    maps = komsu["maps"]
    if not 0 <= map_number < len(maps):
        map_number = 0
    neighbor_info = {
        "result": "ok",
        "processed_errors": 0,
        "timestamp": timestamp_now(),
        "playerInfo": komsu["playerInfo"],
        "map": maps[map_number],
        "privateState": komsu["privateState"],
        "neighbors": neighbors(userid)
    }
    return neighbor_info
