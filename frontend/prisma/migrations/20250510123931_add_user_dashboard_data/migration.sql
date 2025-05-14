-- CreateTable
CREATE TABLE "user_dashboard_data" (
    "user_id" TEXT NOT NULL,
    "total_points" INTEGER NOT NULL DEFAULT 0,
    "previous_session_points" INTEGER NOT NULL DEFAULT 0,
    "points_history" TEXT NOT NULL DEFAULT '[]',

    CONSTRAINT "user_dashboard_data_pkey" PRIMARY KEY ("user_id")
);

-- AddForeignKey
ALTER TABLE "user_dashboard_data" ADD CONSTRAINT "user_dashboard_data_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "User"("id") ON DELETE CASCADE ON UPDATE CASCADE;
